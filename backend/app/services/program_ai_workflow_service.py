import json
import hashlib
from datetime import date, datetime, timezone
from typing import Any
from urllib.parse import parse_qsl, urlencode, urldefrag, urlparse, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment, CommitmentEvidenceLink, CommitmentStatusUpdate
from app.models.evidence import EvidenceItem
from app.models.program import Program, ProgramAiExtraction, ProgramSection
from app.services.commitment_service import (
    BASELINE_MODES,
    COMMITMENT_STATUSES,
    COMMITMENT_TYPES,
    COMMITMENT_EVIDENCE_RELATION_TYPES,
    CONFIDENCE_LEVELS,
    CONTRIBUTION_LEVELS,
    CONTRIBUTION_TYPES,
    CONTROL_LEVELS,
    EVIDENCE_ROLES,
    EVIDENCE_SOURCE_TYPES,
    EVIDENCE_STRENGTHS,
    IMPORTANCE_LEVELS,
    MATERIALITY_LEVELS,
    MEASURE_VALIDITY_STATUSES,
    commitment_importance_weight,
    ensure_unique_slug,
    optional_text,
    status_group,
)
from app.services.commitment_analysis_methodology import (
    CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY,
    COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
    CONCLUSION_BASES,
    DEADLINE_TYPES,
    EVIDENCE_GAP_KINDS,
    IMPLEMENTATION_DIMENSION_STATUSES,
    MATERIAL_COMPONENT_STATUSES,
    commitment_analysis_output_schema,
)
from app.services.prompt_schema_builder import db_fields_contract, enum_contract

PROGRAM_AI_PROMPT_VERSION = "mvp-6"
PROGRAM_AI_SCHEMA_VERSION = "mvp-6"

PROGRAM_STRUCTURE_TASK = "program_structure_extraction"
SECTION_REFINEMENT_TASK = "program_section_structure_refinement"
COMMITMENT_STATUS_TASK = "commitment_status_analysis"
SECTION_BATCH_STATUS_TASK = "program_section_commitment_status_batch_analysis"
SECTION_SUMMARY_TASK = "program_section_summary_analysis"

PROGRAM_AI_TASK_TYPES = {
    PROGRAM_STRUCTURE_TASK,
    SECTION_REFINEMENT_TASK,
    COMMITMENT_STATUS_TASK,
    SECTION_BATCH_STATUS_TASK,
    SECTION_SUMMARY_TASK,
}

MODEL_OUTPUT_METADATA_BOUNDARY = """Metadata boundary:
- The JSON schema below is the model content contract only.
- The backend/CLI stores prompt_version, schema_version, methodology_version, model_name/model type, task type, target binding, analysis date, token counts, and tool counts on the AI run outside this JSON."""

STATUS_MODEL_OUTPUT_METADATA_CONTRACT = f"""Status response metadata contract:
- Return model_name at the top level as the exact model name/version used for this response.
- Return prompt_version exactly "{PROGRAM_AI_PROMPT_VERSION}".
- Return schema_version exactly "{PROGRAM_AI_SCHEMA_VERSION}".
- Return methodology_version exactly "{COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}".
- Do not return other metadata. Do not return backend IDs, target IDs, task type, analysis date, token counts, tool counts, review flags, status_group, importance_weight, or any numeric scoring fields."""

TARGET_COMMITMENT_REF = "TARGET_COMMITMENT"
TARGET_SECTION_REF = "TARGET_SECTION"
AI_RUN_IMPORTED_STATUS = "imported"
AI_RUN_NO_IMPORT_STATUS = "no_import"

ALLOWED_STATUS_GROUPS = {"pending", "active", "completed", "failed", "unclear"}
IMPLEMENTATION_STATUSES = {key for key in COMMITMENT_STATUSES if key != "not_analyzed"}
SOURCE_ACQUISITION_METHODS = {
    "provided_full_text",
    "provided_url",
    "provided_url_with_additional_search",
    "independent_official_source_search",
    "partial_source",
    "source_not_found",
}
SOURCE_COVERAGE_STATUSES = {"full", "partial", "unknown"}
FORBIDDEN_STRUCTURE_STATUS_FIELDS = {
    "status",
    "current_status",
    "status_group",
    "implementation_status",
    "implementation_progress",
    "fulfilled",
    "unfulfilled",
    "violated",
    "in_progress",
    "partially_fulfilled",
    "not_started",
    "abandoned",
    "completed",
    "failed",
    "confidence_of_status",
    "status_explanation",
}

STATUS_GROUP_BY_STATUS = {
    status: status_group(status)
    for status in IMPLEMENTATION_STATUSES
}

DEFAULT_CONTRIBUTION_LEVEL = "indeterminate"

MAX_SECTION_DEPTH = 8


def _user_id(user: dict | None):
    moderator = user.get("moderator") if user else None
    return moderator.id if moderator else None


def _json_error_context(raw_json: str, position: int, radius: int = 120) -> str:
    start = max(position - radius, 0)
    end = min(position + radius, len(raw_json))
    excerpt = raw_json[start:end].replace("\n", "\\n")
    pointer = " " * max(position - start, 0) + "^"
    return f"{excerpt}\n{pointer}"


def parse_json(raw_json: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}\n{_json_error_context(raw_json, exc.pos)}") from exc
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")
    return data


def parse_date_or_none(value: str | None) -> date | None:
    if value in (None, "", "YYYY-MM-DD or null"):
        return None
    if not isinstance(value, str):
        raise ValueError(f"Invalid date: {value}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid date: {value}") from exc


def validate_url_or_none(value: Any, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string or null.")
    normalized = value.strip()
    parsed = urlparse(normalized)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{field_name} must be an absolute HTTP(S) URL or null.")
    return normalized


def _int_or_default(value: Any, field_name: str, default: int = 0) -> int:
    if value in (None, ""):
        return default
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def _enum_or_none(value: Any, allowed: set[str], field_name: str) -> str | None:
    value = optional_text(value)
    if value is None:
        return None
    if value not in allowed:
        raise ValueError(f"{field_name} is invalid.")
    return value


def _enum_required(value: Any, allowed: set[str], field_name: str) -> str:
    value = optional_text(value)
    if value is None:
        raise ValueError(f"{field_name} is required.")
    if value not in allowed:
        raise ValueError(f"{field_name} is invalid.")
    return value


def _string_list_or_text(value: Any, field_name: str) -> str | None:
    if value in (None, ""):
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "\n".join(item.strip() for item in value if item.strip()) or None
    raise ValueError(f"{field_name} must be a string, array of strings, or null.")


def _bool_or_default(value: Any, field_name: str, default: bool = False) -> bool:
    if value in (None, ""):
        return default
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field_name} must be boolean.")


def latest_ai_run(db: Session, target_type: str, target_id: UUID, task_type: str) -> AiRun | None:
    return (
        db.query(AiRun)
        .filter(AiRun.target_type == target_type, AiRun.target_id == target_id, AiRun.task_type == task_type)
        .order_by(AiRun.created_at.desc())
        .first()
    )


def _ai_run_has_response_or_import(ai_run: AiRun) -> bool:
    return bool(
        ai_run.raw_ai_response
        or ai_run.parsed_json
        or ai_run.parsed_at
        or ai_run.import_error
        or ai_run.imported_at
        or ai_run.status
        in {
            "response_received",
            "parse_failed",
            "validated",
            "import_failed",
            AI_RUN_IMPORTED_STATUS,
            AI_RUN_NO_IMPORT_STATUS,
        }
    )


def _snapshot_timestamp(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _ref_entry(entity_type: str, entity: Any) -> dict[str, Any]:
    return {
        "entity_type": entity_type,
        "entity_id": str(entity.id),
        "updated_at": _snapshot_timestamp(getattr(entity, "updated_at", None)),
    }


def _fingerprint(input_snapshot: dict[str, Any] | None, local_ref_map: dict[str, Any] | None) -> str:
    serialized = json.dumps(
        {"input_snapshot": input_snapshot or {}, "local_ref_map": local_ref_map or {}},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _sorted_commitments(commitments: list[Commitment]) -> list[Commitment]:
    return sorted(commitments, key=lambda item: (item.display_order, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))


def section_direct_ref_map(section: ProgramSection) -> dict[str, Any]:
    refs = {TARGET_SECTION_REF: _ref_entry("program_section", section)}
    children = sorted(section.child_sections, key=lambda item: (item.display_order, item.created_at or datetime.min.replace(tzinfo=timezone.utc)))
    for index, child in enumerate(children, start=1):
        refs[f"EXISTING_SECTION_{index}"] = _ref_entry("program_section", child)
    for index, commitment in enumerate(_sorted_commitments(list(section.commitments)), start=1):
        refs[f"EXISTING_COMMITMENT_{index}"] = _ref_entry("commitment", commitment)
    return refs


def status_commitment_ref_map(commitment: Commitment) -> dict[str, Any]:
    return {TARGET_COMMITMENT_REF: _ref_entry("commitment", commitment)}


def batch_commitment_ref_map(section: ProgramSection, *, recursive: bool = True) -> dict[str, Any]:
    commitments = section_scope_commitments(section) if recursive else _sorted_commitments(list(section.commitments))
    refs = {TARGET_SECTION_REF: _ref_entry("program_section", section)}
    refs.update({f"COM{index}": _ref_entry("commitment", item) for index, item in enumerate(commitments, start=1)})
    return refs


def ai_run_context(target: Program | ProgramSection | Commitment, task_type: str, *, recursive: bool = True) -> dict[str, Any]:
    analysis_day = date.today() if task_type in {COMMITMENT_STATUS_TASK, SECTION_BATCH_STATUS_TASK, SECTION_SUMMARY_TASK} else None
    if task_type == PROGRAM_STRUCTURE_TASK:
        refs: dict[str, Any] = {}
        snapshot = {
            "program_updated_at": _snapshot_timestamp(getattr(target, "updated_at", None)),
            "title": target.title,
            "program_type": target.program_type,
            "political_subject_name": target.political_subject_name,
            "period_text": target.period_text,
            "source_url": target.source_url,
            "source_title": target.source_title,
            "source_text": _program_full_text(target),
        }
    elif task_type == COMMITMENT_STATUS_TASK:
        refs = status_commitment_ref_map(target)
        snapshot = {"analysis_date": analysis_day.isoformat() if analysis_day else None, "target_ref": TARGET_COMMITMENT_REF}
    elif task_type == SECTION_REFINEMENT_TASK:
        refs = section_direct_ref_map(target)
        snapshot = {"scope": "direct", "target_ref": TARGET_SECTION_REF, "section_original_text": target.original_text}
    else:
        refs = batch_commitment_ref_map(target, recursive=recursive)
        snapshot = {
            "scope": "recursive" if recursive else "direct",
            "analysis_date": analysis_day.isoformat() if analysis_day else None,
            "target_ref": TARGET_SECTION_REF,
        }
    return {"input_snapshot": snapshot, "local_ref_map": refs, "analysis_date": analysis_day}


def create_or_update_ai_run(
    db: Session,
    target_type: str,
    target_id: UUID,
    task_type: str,
    prompt_text: str,
    user: dict | None = None,
    *,
    input_snapshot: dict[str, Any] | None = None,
    local_ref_map: dict[str, Any] | None = None,
    analysis_date: date | None = None,
) -> AiRun:
    latest = latest_ai_run(db, target_type, target_id, task_type)
    if latest and not _ai_run_has_response_or_import(latest):
        ai_run = latest
        ai_run.prompt_text = prompt_text
        ai_run.status = "prompt_generated"
        ai_run.prompt_version = PROGRAM_AI_PROMPT_VERSION
        ai_run.schema_version = PROGRAM_AI_SCHEMA_VERSION
        ai_run.methodology_version = COMMITMENT_ANALYSIS_METHODOLOGY_VERSION
        ai_run.model_name = None
        ai_run.raw_ai_response = None
        ai_run.parsed_json = None
        ai_run.parse_error = None
        ai_run.import_error = None
        ai_run.input_snapshot = input_snapshot or {}
        ai_run.local_ref_map = local_ref_map or {}
        ai_run.input_fingerprint = _fingerprint(input_snapshot, local_ref_map)
        ai_run.analysis_date = analysis_date
        ai_run.response_pasted_at = None
        ai_run.parsed_at = None
        ai_run.validated_at = None
        ai_run.imported_at = None
    else:
        ai_run = AiRun(
            target_type=target_type,
            target_id=target_id,
            task_type=task_type,
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            methodology_version=COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
            prompt_text=prompt_text,
            structural_review_status="not_reviewed",
            factual_review_status="not_reviewed",
            created_by_user_id=_user_id(user),
            input_snapshot=input_snapshot or {},
            local_ref_map=local_ref_map or {},
            input_fingerprint=_fingerprint(input_snapshot, local_ref_map),
            analysis_date=analysis_date,
        )
        db.add(ai_run)
    return ai_run


def ensure_ai_run_importable(ai_run: AiRun) -> None:
    if ai_run.imported_at or ai_run.status in {AI_RUN_IMPORTED_STATUS, AI_RUN_NO_IMPORT_STATUS}:
        raise ValueError("This AI run already has an import outcome. Generate a new prompt before importing again.")


def mark_parse_failed(ai_run: AiRun, raw_json: str, error: str, user: dict | None = None) -> None:
    ai_run.raw_ai_response = raw_json
    ai_run.parsed_json = None
    ai_run.parsed_at = None
    ai_run.parse_error = error
    ai_run.import_error = None
    ai_run.status = "parse_failed"
    ai_run.response_pasted_at = datetime.now(timezone.utc)
    ai_run.response_pasted_by_user_id = _user_id(user)


def mark_validated(ai_run: AiRun, raw_json: str, data: dict[str, Any], user: dict | None = None) -> None:
    if optional_text(data.get("model_name")):
        ai_run.model_name = data["model_name"].strip()
    ai_run.raw_ai_response = raw_json
    ai_run.parsed_json = data
    ai_run.parse_error = None
    ai_run.import_error = None
    ai_run.status = "validated"
    ai_run.response_pasted_at = datetime.now(timezone.utc)
    ai_run.response_pasted_by_user_id = _user_id(user)
    ai_run.parsed_at = datetime.now(timezone.utc)
    ai_run.validated_at = datetime.now(timezone.utc)


def mark_imported(ai_run: AiRun) -> None:
    ai_run.status = AI_RUN_IMPORTED_STATUS
    ai_run.import_error = None
    ai_run.imported_at = datetime.now(timezone.utc)


def mark_parse_success(ai_run: AiRun, raw_json: str, data: dict[str, Any], user: dict | None = None) -> None:
    """Compatibility helper for routes that validate and import in one transaction."""
    mark_validated(ai_run, raw_json, data, user)
    mark_imported(ai_run)


def mark_import_failed(ai_run: AiRun, raw_json: str, data: dict[str, Any], error: str, user: dict | None = None) -> None:
    mark_validated(ai_run, raw_json, data, user)
    ai_run.import_error = error
    ai_run.status = "import_failed"


def mark_no_import(ai_run: AiRun, raw_json: str, data: dict[str, Any], error: str, user: dict | None = None) -> None:
    if optional_text(data.get("model_name")):
        ai_run.model_name = data["model_name"].strip()
    ai_run.raw_ai_response = raw_json
    ai_run.parsed_json = data
    ai_run.parse_error = error
    ai_run.import_error = None
    ai_run.status = AI_RUN_NO_IMPORT_STATUS
    ai_run.response_pasted_at = datetime.now(timezone.utc)
    ai_run.response_pasted_by_user_id = _user_id(user)
    ai_run.parsed_at = datetime.now(timezone.utc)
    ai_run.validated_at = datetime.now(timezone.utc)


def _program_metadata(program: Program) -> str:
    return f"""Program metadata:
Title: {program.title}
Program type: {getattr(program, "program_type", "") or ""}
Political actor: {getattr(program, "political_subject_name", "") or ""}
Period: {getattr(program, "period_text", "") or ""}
Start date: {getattr(program, "period_start", "") or ""}
End date: {getattr(program, "period_end", "") or ""}
Publication date: {getattr(program, "publication_date", "") or ""}
Source URL if available: {getattr(program, "source_url", "") or ""}
Source title if available: {getattr(program, "source_title", "") or ""}"""


def _status_program_ownership_context(program: Program) -> str:
    program_type = getattr(program, "program_type", None) or "other"
    actor = (
        optional_text(getattr(program, "political_subject_name", None))
        or optional_text(getattr(program, "related_coalition_name", None))
        or optional_text(getattr(getattr(program, "related_party", None), "name", None))
        or "not specified"
    )
    if program_type in {"government_program", "government_action_plan"}:
        ownership = "official cabinet/government program"
        warning = "Cabinet responsibility may be assessed only for the stored government actor and the cabinet period supported by evidence."
    elif program_type == "coalition_agreement":
        ownership = "coalition agreement or coalition program"
        warning = "Do not upgrade this source to an official cabinet program unless evidence proves formal government adoption of the specific commitment."
    elif program_type in {"party_program", "election_program", "policy_platform"}:
        ownership = "party or electoral program"
        warning = "Do not treat this as a cabinet commitment merely because the party later joined or supported a cabinet."
    else:
        ownership = "other political program"
        warning = "Use the stored program type and actor; do not infer cabinet ownership without direct evidence."
    return f"""Program ownership for status analysis:
Stored program type: {program_type}
Stored political actor: {actor}
Ownership category: {ownership}
Ownership rule: {warning}"""


def _program_full_text(program: Program) -> str:
    return program.source_description or ""


def _source_retrieval_schema() -> dict[str, Any]:
    return {
        "acquisition_method": enum_contract(SOURCE_ACQUISITION_METHODS),
        "primary_source_title": "string or null",
        "primary_source_url": "string or null",
        "publisher": "string or null",
        "published_at": "YYYY-MM-DD or null",
        "document_complete": db_fields_contract(Program, [("document_complete", "source_document_complete")])["document_complete"],
        "supplementary_source_urls": ["string"],
        "acquisition_note": db_fields_contract(Program, [("acquisition_note", "source_acquisition_note")])["acquisition_note"],
        "coverage_status": enum_contract(SOURCE_COVERAGE_STATUSES),
    }


def _section_structure_item_schema(*, include_operation: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    if include_operation:
        schema.update(
            {
                "operation": "keep | update | create",
                "existing_ref": "EXISTING_SECTION_1 or null",
                "new_ref": "NEW_SECTION_1 or null",
                "parent_ref": TARGET_SECTION_REF,
            }
        )
    else:
        schema.update({"section_ref": "SEC1", "parent_section_ref": None})
    schema.update(
        db_fields_contract(
            ProgramSection,
            [
                "section_code",
                "title",
                "original_heading",
                "original_text",
                "summary",
                "problem_description",
                "policy_area",
                "display_order",
            ],
        )
    )
    return schema


def _commitment_structure_item_schema(*, include_operation: bool = False) -> dict[str, Any]:
    schema: dict[str, Any] = {}
    if include_operation:
        schema.update(
            {
                "operation": "keep | update | create",
                "existing_ref": "EXISTING_COMMITMENT_1 or null",
                "new_ref": "NEW_COMMITMENT_1 or null",
                "section_ref": TARGET_SECTION_REF,
            }
        )
    else:
        schema.update({"commitment_ref": "COM1", "section_ref": "SEC1"})
    schema.update(
        db_fields_contract(
            Commitment,
            [
                "display_code",
                "title",
                "original_text",
                "normalized_description",
                "topic",
                "responsible_institutions_text",
                "period_text",
                "deadline",
                "measurable_criteria",
                "commitment_type",
                "promised_item_type",
                "importance_level",
                "materiality",
                "materiality_reason",
                "display_order",
            ],
            enum_fields={
                "commitment_type": COMMITMENT_TYPES,
                "promised_item_type": COMMITMENT_TYPES,
                "importance_level": IMPORTANCE_LEVELS,
                "materiality": MATERIALITY_LEVELS,
            },
            nullable_overrides={
                "original_text": False,
                "normalized_description": False,
                "commitment_type": False,
                "promised_item_type": False,
                "importance_level": False,
                "materiality": False,
            },
        )
    )
    return schema


def program_structure_prompt_validation_error(program: Program) -> str | None:
    if _program_full_text(program) or program.source_url or program.source_title:
        return None
    if program.title and program.political_subject_name and program.program_type:
        return None
    return (
        "Not enough metadata to generate a web-search structure prompt. "
        "Add a program title, political actor, and program type, or provide a source URL/full text."
    )


def _program_source_input(program: Program) -> str:
    full_text = _program_full_text(program)
    if full_text:
        source_lines = [f"Primary provided full program text:\n{full_text}"]
        if program.source_url:
            source_lines.append(
                "Provided source URL for provenance or fallback retrieval:\n"
                f"{program.source_url}\n\n"
                "If the pasted text is incomplete, use this URL as a primary starting point and report additional retrieval in source_retrieval."
            )
        return "\n\n".join(source_lines)
    if program.source_url:
        return f"""Provided source URL:
{program.source_url}

Use this URL as the primary starting point. If it is incomplete, inaccessible, a landing page, or not the actual official program text/document, search further and report that in source_retrieval."""
    if program.source_title:
        return f"""Provided source metadata:
Source title: {program.source_title}

No source URL was provided. Search the public web for the official program using this source metadata and the program metadata below."""
    return "No source URL was provided.\nSearch the public web for the official program using the metadata below."


def build_program_structure_prompt(program: Program) -> str:
    schema = {
        "source_retrieval": _source_retrieval_schema(),
        "coverage_warnings": ["string"],
        "program_structure": {
            "sections": [_section_structure_item_schema()],
            "commitments": [_commitment_structure_item_schema()],
        },
    }
    return f"""You are extracting the structure of a political program for a public transparency platform.
Return exactly one valid JSON object. Do not include markdown, code fences, a preamble, commentary, or keys outside the contract.
All user-facing text fields must be in Bulgarian. Preserve original document wording in original_heading and original_text.

Task type: {PROGRAM_STRUCTURE_TASK}
Prompt version: {PROGRAM_AI_PROMPT_VERSION}
Schema version: {PROGRAM_AI_SCHEMA_VERSION}

{MODEL_OUTPUT_METADATA_BOUNDARY}

This task requires web access unless full program text is provided.
Use a web-enabled/research-capable model.
You have no access to the platform backend, database, internal records, DB IDs, or system state.
You may use only public web sources and/or the text provided in this prompt.

Source acquisition instructions:
- If full program text is provided below, use it as the primary source.
- If a Source URL is provided, open it first and use it as the primary source.
- If the Source URL is a landing page, follow clearly relevant links to the official program page/PDF/document.
- If no Source URL is provided, search the public web for the official program using the program metadata.
- If the provided source is inaccessible, incomplete, or not the actual program, search for the official source and report this in source_retrieval.acquisition_note.
- Prefer official sources: government websites, party websites, official PDFs, official policy documents, official coalition agreements, official program pages.
- Avoid relying on media reports, summaries, reposts, social media posts, or third-party interpretations unless no official source can be found.
- If only secondary or partial sources are available, use acquisition_method "partial_source", coverage_status "partial", and list every known omission in coverage_warnings.
- If no reliable source can be retrieved, do not invent sections or commitments. Use acquisition_method "source_not_found", coverage_status "unknown", and return empty sections and commitments.

Rules:
- The AI has no access to the platform database. Never ask for, infer, or return database IDs.
- Extract the program hierarchy: sections, subsections, and candidate commitments.
- A section organizes a document theme, public problem, sector, policy area, or group of measures. A subsection is a child section.
- A commitment is the smallest separately trackable promise, measure, reform, action, milestone, quantitative target, deadline, or goal.
- Do not turn background statements, values, diagnoses, rhetoric, or broad aspirations without a trackable action/result into commitments.
- Distinguish promised action from promised result: "will submit a bill" is an action, "will adopt a law" is a legislative result, and "will reduce poverty" is a public outcome.
- Mark maintenance, negative, and conditional commitments explicitly when the original text promises to preserve, avoid, or act only after a condition.
- Set importance_level for every commitment: key, standard, or technical. This is an editorial classification made from the program text and public importance.
- Do not return importance_weight or is_key_commitment. The backend derives numeric importance_weight from importance_level and owns all numeric scoring/aggregation.
- Keep materiality low/medium/high as a separate structural field about how central the promise is inside its source text.
- Do not merge materially independent measures. Do not split one indivisible measure into artificial fragments.
- Cover the complete source in original order. Do not silently skip long, difficult, repetitive, or uncertain areas; describe omissions in coverage_warnings.
- Do not analyze implementation status.
- Do not include current_status, status_group, fulfilled, violated, in_progress, not_started, abandoned, completed, failed, or similar status fields.
- Preserve original wording where possible.
- Use temporary local refs only: SEC1, SEC2, COM1, COM2. These are not database IDs.
- Make uncertainty explicit in summaries/descriptions instead of inventing details.
- Do not invent sources, quotes, dates, institutions, headings, sections, commitments, deadlines, or criteria.
- Use null only where the schema says "or null". Use only the enum values shown in the contract.

Expected JSON schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

{_program_metadata(program)}

Source input:
{_program_source_input(program)}
"""


def _section_context(section: ProgramSection) -> str:
    refs = section_direct_ref_map(section)
    section_ref_by_id = {entry["entity_id"]: ref for ref, entry in refs.items() if entry["entity_type"] == "program_section"}
    commitment_ref_by_id = {entry["entity_id"]: ref for ref, entry in refs.items() if entry["entity_type"] == "commitment"}
    child_sections = [
        {
            "existing_ref": section_ref_by_id[str(child.id)],
            "section_code": child.section_code,
            "title": child.title,
            "original_heading": child.original_heading,
            "original_text": child.original_text,
            "summary": child.summary,
            "display_order": child.display_order,
        }
        for child in sorted(section.child_sections, key=lambda item: (item.display_order, item.created_at))
    ]
    commitments = [
        {
            "existing_ref": commitment_ref_by_id[str(item.id)],
            "display_code": item.display_code,
            "title": item.title,
            "original_text": item.original_text,
            "normalized_description": item.normalized_description,
            "display_order": item.display_order,
        }
        for item in _sorted_commitments(list(section.commitments))
    ]
    return json.dumps({"existing_child_sections": child_sections, "existing_commitments": commitments}, indent=2, ensure_ascii=False)


def build_section_refinement_prompt(section: ProgramSection) -> str:
    schema = {
        "section_structure": {
            "sections": [_section_structure_item_schema(include_operation=True)],
            "commitments": [_commitment_structure_item_schema(include_operation=True)],
        },
    }
    program = section.program
    return f"""You are refining the structure under one selected program section.
Return exactly one valid JSON object. Do not include markdown, code fences, a preamble, commentary, or additional keys.
All user-facing text fields must be in Bulgarian and original text must preserve the source wording.

Task type: {SECTION_REFINEMENT_TASK}
Prompt version: {PROGRAM_AI_PROMPT_VERSION}
Schema version: {PROGRAM_AI_SCHEMA_VERSION}

{MODEL_OUTPUT_METADATA_BOUNDARY}

Rules:
- The selected section local ref is {TARGET_SECTION_REF}. This is not a database ID.
- Do not return a top-level target object; the backend binds this response to the stored AI run.
- Add or refine child sections and candidate commitments only under the selected section.
- Use operation "update" or "keep" with an exact existing_ref for existing records.
- Use operation "create", a unique new_ref, and an allowed parent/section ref for new records.
- Omission never deletes an existing record. Do not return deletion operations.
- Do not duplicate an existing item under a new title or fuzzy match records by title.
- Do not analyze implementation status.
- Do not include status, current_status, status_group, fulfilled, violated, in_progress, or similar fields.
- Set importance_level for created commitments and update it only when the section evidence supports a better classification: key, standard, or technical.
- Do not return importance_weight or is_key_commitment. The backend derives numeric importance_weight from importance_level and owns all numeric scoring/aggregation.
- Use temporary local refs for new records, such as NEW_SECTION_1 and NEW_COMMITMENT_1. These are not database IDs.
- Do not invent source wording, measures, dates, institutions, or criteria. Report uncertainty with null where allowed.

Expected JSON schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

{_program_metadata(program)}

Selected section:
Code: {section.section_code or ""}
Title: {section.title}
Original text:
{section.original_text or ""}
Summary:
{section.summary or ""}

Existing structure under the selected section:
{_section_context(section)}
"""


def _commitment_text(commitment: Commitment) -> str:
    return optional_text(getattr(commitment, "original_text", None)) or optional_text(getattr(commitment, "normalized_description", None)) or ""


def _normalized_text(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _parent_commitment(commitment: Commitment) -> Commitment | None:
    parent = getattr(commitment, "parent_commitment", None)
    if parent is not None:
        return parent
    parent_id = getattr(commitment, "parent_commitment_id", None)
    program = getattr(commitment, "program", None)
    if not parent_id or not program or not getattr(program, "commitments", None):
        return None
    return next((item for item in program.commitments if getattr(item, "id", None) == parent_id), None)


def _child_commitments(commitment: Commitment) -> list[Commitment]:
    program = getattr(commitment, "program", None)
    if not program or not getattr(program, "commitments", None):
        return []
    commitment_id = getattr(commitment, "id", None)
    return [item for item in program.commitments if getattr(item, "parent_commitment_id", None) == commitment_id]


def _commitment_ancestors(commitment: Commitment) -> list[Commitment]:
    ancestors: list[Commitment] = []
    seen: set[Any] = set()
    parent = _parent_commitment(commitment)
    while parent is not None and getattr(parent, "id", id(parent)) not in seen:
        seen.add(getattr(parent, "id", id(parent)))
        ancestors.append(parent)
        parent = _parent_commitment(parent)
    return list(reversed(ancestors))


def _is_context_fragment(commitment: Commitment) -> bool:
    original = optional_text(getattr(commitment, "original_text", None)) or ""
    normalized = optional_text(getattr(commitment, "normalized_description", None)) or ""
    text = original or normalized
    if not text:
        return True
    lowered = text.strip().lower()
    starts_contextual = lowered.startswith(("for ", "за ", "относно ", "при ", "в рамките на "))
    short = len(lowered.split()) <= 5
    return starts_contextual and short and not normalized


def _status_prompt_scope_error(commitment: Commitment) -> str | None:
    program = getattr(commitment, "program", None)
    review_status = getattr(program, "structural_review_status", "passed") if program is not None else "passed"
    if review_status != "passed":
        return "Status analysis prompt requires the program structure to pass structural review first."
    text = _commitment_text(commitment)
    parent = _parent_commitment(commitment)
    if _is_context_fragment(commitment) and parent is None:
        return "Selected commitment is a context-dependent fragment without a parent hierarchy; review the structure before status analysis."
    parent_text = _commitment_text(parent) if parent is not None else ""
    if parent_text and _normalized_text(parent_text) == _normalized_text(text):
        return "Selected commitment duplicates its parent text; review the structure to avoid double counting."
    for child in _child_commitments(commitment):
        child_text = _commitment_text(child)
        if _normalized_text(child_text) == _normalized_text(text) or _is_context_fragment(child):
            return "Selected parent commitment has overlapping or context-dependent child commitments; analyze the child scope or review the structure first."
    return None


def _ensure_status_prompt_scope(commitment: Commitment) -> None:
    error = _status_prompt_scope_error(commitment)
    if error:
        raise ValueError(error)


def _commitment_hierarchy_context(commitment: Commitment) -> str:
    ancestors = _commitment_ancestors(commitment)
    if not ancestors:
        return "Parent hierarchy: none"
    entries = []
    for index, ancestor in enumerate(ancestors, start=1):
        entries.append(
            {
                "level": index,
                "title": getattr(ancestor, "title", None),
                "original_text": getattr(ancestor, "original_text", None),
                "normalized_description": getattr(ancestor, "normalized_description", None),
            }
        )
    return "Parent hierarchy context (for meaning only; do not score parent text as this commitment):\n" + json.dumps(
        entries,
        indent=2,
        ensure_ascii=False,
    )


def _commitment_context(commitment: Commitment, commitment_ref: str) -> str:
    section = commitment.program_section.title if commitment.program_section else ""
    return f"""Program: {commitment.program.title if commitment.program else ""}
Section: {section}
Commitment ref: {commitment_ref}
{_commitment_hierarchy_context(commitment)}
Commitment title: {commitment.title}
Original text: {commitment.original_text or ""}
Normalized description: {commitment.normalized_description or ""}
Period: {commitment.period_text or ""}
Responsible institutions: {commitment.responsible_institutions_text or ""}
Measurable criteria: {commitment.measurable_criteria or ""}
Deadline: {commitment.deadline or ""}
Backend-supplied importance level: {getattr(commitment, "importance_level", None) or "standard"}
Backend-derived importance weight: {commitment_importance_weight(commitment)}"""


def _status_metadata_contract() -> dict[str, Any]:
    return {
        "model_name": "string",
        "prompt_version": PROGRAM_AI_PROMPT_VERSION,
        "schema_version": PROGRAM_AI_SCHEMA_VERSION,
        "methodology_version": COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
    }


def _commitment_status_response_contract(commitment_ref: str) -> dict[str, Any]:
    schema = commitment_analysis_output_schema(commitment_ref)
    return {
        **_status_metadata_contract(),
        "target": {"type": "commitment", "commitment_ref": commitment_ref},
        "commitment_analysis": schema["commitment_analysis"],
        "sources": schema["sources"],
    }


def _section_batch_status_response_contract(commitment_ref: str) -> dict[str, Any]:
    schema = commitment_analysis_output_schema(commitment_ref)
    return {
        **_status_metadata_contract(),
        "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
        "commitment_analyses": [schema["commitment_analysis"]],
        "sources": schema["sources"],
    }


def build_commitment_status_prompt(
    commitment: Commitment,
    *,
    commitment_ref: str = TARGET_COMMITMENT_REF,
    analysis_date: date | None = None,
    batch_context: str | None = None,
) -> str:
    _ensure_status_prompt_scope(commitment)
    effective_date = analysis_date or date.today()
    schema = _commitment_status_response_contract(commitment_ref)
    batch_instruction = f"\n- Batch context: {batch_context}" if batch_context else ""
    return f"""You are analyzing implementation status for one political commitment as of {effective_date.isoformat()}.
Return exactly one valid JSON object. Do not include markdown, code fences, a preamble, commentary, or additional keys.
All user-facing explanations must be in Bulgarian.

Task type: {COMMITMENT_STATUS_TASK}
Prompt version: {PROGRAM_AI_PROMPT_VERSION}
Schema version: {PROGRAM_AI_SCHEMA_VERSION}
Methodology version: {COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}

{STATUS_MODEL_OUTPUT_METADATA_CONTRACT}

Canonical per-commitment methodology:
{CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY}

Task-specific instructions:
- The target commitment local ref is {commitment_ref}. This is not a database ID.
- You have no access to the platform backend, database, internal records, database IDs, or system state.
- Classify only this commitment, not the whole section or program.
- Perform a fresh current-state analysis. No previous analysis or section conclusion is supplied, and neither may be assumed.
- The backend-supplied importance is context only. Do not infer or return importance_level or importance_weight.
- Use top-level target exactly as shown in the contract.
- For maintenance and negative promises, use kept_to_date while the promised condition is still preserved; after the period ends, convert to fulfilled or violated when evidence supports that historical finding.
- Use condition_not_met when an explicit condition has not occurred; use not_due when the deadline/period is not yet due; use delayed for official postponement or material delay.
- Every material component must have a unique local component_ref. Use those refs in claim-specific evidence links.
- Source refs are response-wide. Every evidence link must reference a source in this response and each source must support or limit at least one claim.
- If quantitative_actual is present, quantitative_actual_as_of must be present and supported by a dated or access-dated source.
- Use only enum values in the contract and null only where explicitly allowed.{batch_instruction}

{_program_metadata(commitment.program)}

{_status_program_ownership_context(commitment.program)}

Commitment data:
{_commitment_context(commitment, commitment_ref)}

Verified evidence supplied by the backend:
None. Research and verify current sources independently for this analysis date.

Unverified historical analysis:
Withheld from initial classification. Do not reconstruct or assume a previous conclusion.

Model output contract:
{json.dumps(schema, indent=2, ensure_ascii=False)}
"""


def section_scope_commitments(section: ProgramSection) -> list[Commitment]:
    items = list(section.commitments)
    for child in section.child_sections:
        items.extend(section_scope_commitments(child))
    return _sorted_commitments(items)


def commitment_local_ref_map(commitments: list[Commitment]) -> dict[str, Commitment]:
    return {f"COM{index}": commitment for index, commitment in enumerate(commitments, start=1)}


def build_section_batch_status_prompt(
    section: ProgramSection,
    *,
    recursive: bool = True,
    commitment_refs: list[str] | None = None,
) -> str:
    scoped_items = section_scope_commitments(section) if recursive else _sorted_commitments(list(section.commitments))
    commitments = commitment_local_ref_map(scoped_items)
    selected_refs = commitment_refs or list(commitments)
    unknown_refs = [ref for ref in selected_refs if ref not in commitments]
    if unknown_refs:
        raise ValueError(f"Unknown commitment refs for this section scope: {unknown_refs}")
    selected_commitments = {ref: commitments[ref] for ref in selected_refs}
    for commitment in selected_commitments.values():
        _ensure_status_prompt_scope(commitment)
    output_contract = _section_batch_status_response_contract(selected_refs[0] if selected_refs else "COM1")
    commitment_context = "\n\n---\n\n".join(
        _commitment_context(commitment, ref)
        for ref, commitment in selected_commitments.items()
    )
    return f"""You are analyzing implementation status for a tranche of political commitments as of {date.today().isoformat()}.
Return exactly one valid JSON object. Do not include markdown, code fences, a preamble, commentary, or additional keys.
All user-facing explanations must be in Bulgarian.

Batch task type: {SECTION_BATCH_STATUS_TASK}
Prompt version: {PROGRAM_AI_PROMPT_VERSION}
Schema version: {PROGRAM_AI_SCHEMA_VERSION}
Methodology version: {COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}
Analysis date: {date.today().isoformat()}
Scope: {"full descendant subtree" if recursive else "direct commitments only"}
Tranche item count: {len(selected_commitments)}
Expected commitment refs in this tranche: {", ".join(selected_refs)}

{STATUS_MODEL_OUTPUT_METADATA_CONTRACT}

Canonical per-commitment methodology:
{CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY}

Task-specific instructions:
- Analyze each listed commitment independently with the same depth you would apply to a standalone commitment prompt.
- Return exactly one commitment_analysis object for every listed local ref and for no other refs.
- Do not use previous platform status, previous analyses, section summaries, aggregate conclusions, or assumptions from nearby commitments as evidence.
- Shared research may be reused only when the source genuinely supports the specific claim for the specific commitment.
- Source refs are response-wide. A source shared by multiple commitments must appear once in sources and be reused by source_ref in claim-specific evidence links.
- Return top-level target exactly as shown in the contract. Do not return backend IDs, task type, analysis date, status_group, importance_level, importance_weight, human-review decisions, or numeric scoring fields.
- Never give the section itself an implementation status. Section summaries are generated later, after item-level analyses are imported.

{_program_metadata(section.program)}

{_status_program_ownership_context(section.program)}

Selected section:
Code: {section.section_code or ""}
Title: {section.title}

Commitments in this tranche:
{commitment_context}

Verified evidence supplied by the backend:
None. Research and verify current sources independently for this analysis date.

Unverified historical analysis:
Withheld from initial classification. Do not reconstruct or assume a previous conclusion.

Model output contract:
{json.dumps(output_contract, indent=2, ensure_ascii=False)}
"""


def section_statistics(section: ProgramSection) -> dict[str, Any]:
    commitments = section_scope_commitments(section)
    counts = {key: 0 for key in COMMITMENT_STATUSES}
    for commitment in commitments:
        effective_status = commitment.current_status if getattr(commitment, "status_updates", None) else "not_analyzed"
        counts[effective_status] = counts.get(effective_status, 0) + 1
    analyzed = len(commitments) - counts.get("not_analyzed", 0)
    analysis_dates = [item.last_status_update for item in commitments if item.last_status_update]
    return {
        "total_commitments": len(commitments),
        "analyzed_commitments": analyzed,
        "not_analyzed_commitments": counts.get("not_analyzed", 0),
        "counts_by_status": counts,
        "direct_commitments": len(section.commitments),
        "descendant_commitments": len(commitments) - len(section.commitments),
        "high_materiality_commitments": sum(1 for item in commitments if item.materiality == "high"),
        "last_successful_analysis_date": max(analysis_dates).isoformat() if analysis_dates else None,
    }


def section_summary_readiness_error(section: ProgramSection) -> str | None:
    commitments = section_scope_commitments(section)
    incomplete = [item for item in commitments if not getattr(item, "status_updates", None)]
    if incomplete:
        return (
            f"Section summary requires validated item-level analyses for every commitment. "
            f"{len(incomplete)} of {len(commitments)} commitments are not analyzed."
        )
    return None


def build_section_summary_prompt(section: ProgramSection) -> str:
    readiness_error = section_summary_readiness_error(section)
    if readiness_error:
        raise ValueError(readiness_error)
    commitments = commitment_local_ref_map(section_scope_commitments(section))
    status_context = [
        {
            "commitment_ref": ref,
            "title": commitment.title,
            "current_status": commitment.current_status if getattr(commitment, "status_updates", None) else "not_analyzed",
            "status_group": commitment.status_group if getattr(commitment, "status_updates", None) else "pending",
            "status_explanation": commitment.status_explanation if getattr(commitment, "status_updates", None) else None,
            "confidence": commitment.confidence if getattr(commitment, "status_updates", None) else None,
            "evidence_summaries": [
                {
                    "title": link.title,
                    "relation_type": link.relation_type,
                    "description": link.description,
                }
                for link in commitment.evidence_links
            ],
        }
        for ref, commitment in commitments.items()
    ]
    schema = {
        "section_summary": {
            "summary": "string",
            "problem_description": "string or null",
            "aggregate_status_summary": "string or null",
            "key_findings": ["string"],
        },
    }
    return f"""You are summarizing one program section for a public transparency platform as of {date.today().isoformat()}.
Return exactly one valid JSON object. Do not include markdown, code fences, a preamble, commentary, or additional keys.
All user-facing text must be in Bulgarian.

Task type: {SECTION_SUMMARY_TASK}
Prompt version: {PROGRAM_AI_PROMPT_VERSION}
Schema version: {PROGRAM_AI_SCHEMA_VERSION}

{MODEL_OUTPUT_METADATA_BOUNDARY}

Rules:
- The target section local ref is {TARGET_SECTION_REF}. This is not a database ID.
- Do not return target, prompt_version, schema_version, task type, analysis date, model metadata, or aggregate counts; the backend owns them.
- Update narrative section fields only.
- Do not update commitment statuses.
- Do not assign a hard implementation status to the section.
- Base aggregate status summary on the existing commitment statuses below.
- Treat backend-computed counts as authoritative. Do not recalculate, reclassify, or invent commitment results.
- "not_analyzed" means no successful status analysis; it is different from analyzed status "unclear".
- Do not describe the section itself as fulfilled, unfulfilled, completed, failed, or assigned any hard implementation status.

Expected JSON schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

{_program_metadata(section.program)}

Selected section:
Code: {section.section_code or ""}
Title: {section.title}
Original text:
{section.original_text or ""}

Existing commitment status context:
{json.dumps(status_context, indent=2, ensure_ascii=False)}

Backend-computed section statistics:
{json.dumps(section_statistics(section), indent=2, ensure_ascii=False)}
"""


def _reject_forbidden_structure_fields(value: Any, path: str = "root") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in FORBIDDEN_STRUCTURE_STATUS_FIELDS:
                raise ValueError(f"Structure payload must not include implementation status field at {path}.{key}.")
            _reject_forbidden_structure_fields(child, f"{path}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_forbidden_structure_fields(child, f"{path}[{index}]")


def _structure_object(data: dict[str, Any], key: str) -> dict[str, Any]:
    structure = data.get(key)
    if not isinstance(structure, dict):
        raise ValueError(f"Missing {key} object.")
    return structure


def _reject_unknown_keys(value: dict[str, Any], allowed: set[str], path: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{path} contains unknown keys: {', '.join(sorted(unknown))}.")


def _validate_response_meta(data: dict[str, Any], allowed_top_level: set[str]) -> None:
    _reject_unknown_keys(data, {"model_name", "prompt_version", "schema_version", "methodology_version"} | allowed_top_level, "root")
    if data.get("model_name") is not None and not optional_text(data.get("model_name")):
        raise ValueError("model_name must be a nonempty string when supplied.")
    if data.get("prompt_version") not in {None, "mvp-5", PROGRAM_AI_PROMPT_VERSION}:
        raise ValueError(f"Unsupported legacy prompt_version: {data.get('prompt_version')}.")
    if data.get("schema_version") not in {None, "mvp-5", PROGRAM_AI_SCHEMA_VERSION}:
        raise ValueError(f"Unsupported legacy schema_version: {data.get('schema_version')}.")
    if data.get("methodology_version") not in {None, COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}:
        raise ValueError(f"Unsupported methodology_version: {data.get('methodology_version')}.")


def _validate_status_response_meta(data: dict[str, Any], allowed_top_level: set[str]) -> bool:
    _validate_response_meta(data, allowed_top_level)
    strict = data.get("schema_version") != "mvp-5"
    if strict:
        if not optional_text(data.get("model_name")):
            raise ValueError("model_name is required for status schema mvp-6.")
        if data.get("prompt_version") != PROGRAM_AI_PROMPT_VERSION:
            raise ValueError(f"prompt_version must be {PROGRAM_AI_PROMPT_VERSION}.")
        if data.get("schema_version") != PROGRAM_AI_SCHEMA_VERSION:
            raise ValueError(f"schema_version must be {PROGRAM_AI_SCHEMA_VERSION}.")
        if data.get("methodology_version") != COMMITMENT_ANALYSIS_METHODOLOGY_VERSION:
            raise ValueError(f"methodology_version must be {COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}.")
    return strict


def validate_source_retrieval(data: dict[str, Any]) -> dict[str, Any]:
    source_retrieval = data.get("source_retrieval")
    if not isinstance(source_retrieval, dict):
        raise ValueError("Missing source_retrieval object.")
    _reject_unknown_keys(
        source_retrieval,
        {
            "acquisition_method",
            "primary_source_title",
            "primary_source_url",
            "publisher",
            "published_at",
            "document_complete",
            "supplementary_source_urls",
            "acquisition_note",
            "coverage_status",
        },
        "source_retrieval",
    )
    method = source_retrieval.get("acquisition_method")
    if method not in SOURCE_ACQUISITION_METHODS:
        raise ValueError("source_retrieval.acquisition_method is invalid.")
    coverage = source_retrieval.get("coverage_status")
    if coverage not in SOURCE_COVERAGE_STATUSES:
        raise ValueError("source_retrieval.coverage_status is invalid.")
    document_complete = source_retrieval.get("document_complete")
    if document_complete is not None and not isinstance(document_complete, bool):
        raise ValueError("source_retrieval.document_complete must be boolean or null.")
    additional_urls = source_retrieval.get("supplementary_source_urls") or []
    if not isinstance(additional_urls, list) or any(not optional_text(item) for item in additional_urls if isinstance(item, str)) or any(
        not isinstance(item, str) for item in additional_urls
    ):
        raise ValueError("source_retrieval.supplementary_source_urls must be a list of nonempty strings.")
    validate_url_or_none(source_retrieval.get("primary_source_url"), "source_retrieval.primary_source_url")
    for index, url in enumerate(additional_urls):
        validate_url_or_none(url, f"source_retrieval.supplementary_source_urls[{index}]")
    parse_date_or_none(source_retrieval.get("published_at"))
    if method == "source_not_found":
        if coverage != "unknown" or document_complete is True:
            raise ValueError('source_not_found requires coverage_status "unknown" and document_complete false or null.')
    if method == "partial_source" and coverage != "partial":
        raise ValueError('partial_source requires coverage_status "partial".')
    return source_retrieval


def source_retrieval_failed(data: dict[str, Any]) -> bool:
    source_retrieval = data.get("source_retrieval")
    return isinstance(source_retrieval, dict) and source_retrieval.get("acquisition_method") == "source_not_found"


def _validate_section_tree(sections: list[dict[str, Any]], allowed_parent_refs: set[str] | None = None) -> set[str]:
    allowed_parent_refs = allowed_parent_refs or set()
    section_refs: set[str] = set()
    parent_map: dict[str, str | None] = {}
    for index, section in enumerate(sections, start=1):
        if not isinstance(section, dict):
            raise ValueError(f"sections[{index}] must be an object.")
        _reject_unknown_keys(
            section,
            {
                "section_ref",
                "parent_section_ref",
                "section_code",
                "title",
                "original_heading",
                "original_text",
                "summary",
                "problem_description",
                "policy_area",
                "display_order",
            },
            f"sections[{index}]",
        )
        ref = optional_text(section.get("section_ref"))
        if not ref:
            raise ValueError(f"sections[{index}].section_ref is required.")
        if ref in section_refs:
            raise ValueError(f"Duplicate section_ref: {ref}")
        if ref == TARGET_SECTION_REF:
            raise ValueError(f"section_ref {TARGET_SECTION_REF} is reserved for the selected existing section.")
        section_refs.add(ref)
        parent_ref = optional_text(section.get("parent_section_ref"))
        if parent_ref == ref:
            raise ValueError(f"Section {ref} cannot be its own parent.")
        if not optional_text(section.get("title")):
            raise ValueError(f"sections[{index}].title is required.")
        _int_or_default(section.get("display_order"), f"sections[{index}].display_order")
        parent_map[ref] = parent_ref

    for ref, parent_ref in parent_map.items():
        if parent_ref and parent_ref not in section_refs and parent_ref not in allowed_parent_refs:
            raise ValueError(f"Unknown parent_section_ref for section {ref}: {parent_ref}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(ref: str) -> None:
        if ref in visited:
            return
        if ref in visiting:
            raise ValueError(f"Circular section parent chain involving {ref}.")
        visiting.add(ref)
        parent_ref = parent_map.get(ref)
        if parent_ref in section_refs:
            visit(parent_ref)
        visiting.remove(ref)
        visited.add(ref)

    for ref in section_refs:
        visit(ref)
        depth = 0
        parent_ref = parent_map.get(ref)
        while parent_ref in section_refs:
            depth += 1
            if depth > MAX_SECTION_DEPTH:
                raise ValueError(f"Section hierarchy exceeds maximum depth {MAX_SECTION_DEPTH} at {ref}.")
            parent_ref = parent_map.get(parent_ref)
    return section_refs


def validate_structure_json(
    data: dict[str, Any],
    *,
    structure_key: str = "program_structure",
    allowed_section_refs: set[str] | None = None,
    require_source_retrieval: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if require_source_retrieval:
        _validate_response_meta(data, {"source_retrieval", "coverage_warnings", structure_key})
        warnings = data.get("coverage_warnings") or []
        if not isinstance(warnings, list) or any(not isinstance(item, str) for item in warnings):
            raise ValueError("coverage_warnings must be a list of strings.")
        source_retrieval = validate_source_retrieval(data)
    else:
        _validate_response_meta(data, {"target", structure_key})
        source_retrieval = None
    structure = _structure_object(data, structure_key)
    _reject_forbidden_structure_fields(structure, structure_key)
    sections = structure.get("sections")
    commitments = structure.get("commitments")
    if not isinstance(sections, list):
        raise ValueError(f"{structure_key}.sections must be a list.")
    if not isinstance(commitments, list):
        raise ValueError(f"{structure_key}.commitments must be a list.")
    if source_retrieval and source_retrieval["acquisition_method"] == "source_not_found" and (sections or commitments):
        raise ValueError('program_structure must be empty when source_retrieval.acquisition_method is "source_not_found".')

    known_section_refs = _validate_section_tree(sections, allowed_section_refs)
    all_section_refs = known_section_refs | (allowed_section_refs or set())

    commitment_refs = set()
    for index, commitment in enumerate(commitments, start=1):
        if not isinstance(commitment, dict):
            raise ValueError(f"commitments[{index}] must be an object.")
        _reject_unknown_keys(
            commitment,
            {
                "commitment_ref",
                "section_ref",
                "display_code",
                "title",
                "original_text",
                "normalized_description",
                "topic",
                "responsible_institutions_text",
                "period_text",
                "deadline",
                "measurable_criteria",
                "commitment_type",
                "promised_item_type",
                "importance_level",
                "materiality",
                "materiality_reason",
                "display_order",
            },
            f"commitments[{index}]",
        )
        ref = optional_text(commitment.get("commitment_ref"))
        if not ref:
            raise ValueError(f"commitments[{index}].commitment_ref is required.")
        if ref in commitment_refs:
            raise ValueError(f"Duplicate commitment_ref: {ref}")
        commitment_refs.add(ref)
        section_ref = optional_text(commitment.get("section_ref"))
        if section_ref and section_ref not in all_section_refs:
            raise ValueError(f"Unknown section_ref for commitment {ref}: {section_ref}")
        if not optional_text(commitment.get("title")):
            raise ValueError(f"commitments[{index}].title is required.")
        if not optional_text(commitment.get("original_text")):
            raise ValueError(f"commitments[{index}].original_text is required.")
        _int_or_default(commitment.get("display_order"), f"commitments[{index}].display_order")
        parse_date_or_none(commitment.get("deadline"))
        _enum_or_none(commitment.get("commitment_type"), set(COMMITMENT_TYPES), f"commitments[{index}].commitment_type")
        _enum_or_none(commitment.get("promised_item_type"), set(COMMITMENT_TYPES), f"commitments[{index}].promised_item_type")
        _enum_required(commitment.get("importance_level"), set(IMPORTANCE_LEVELS), f"commitments[{index}].importance_level")
        _enum_or_none(commitment.get("materiality"), set(MATERIALITY_LEVELS), f"commitments[{index}].materiality")
    return sections, commitments


def _validate_ref_target(data: dict[str, Any], expected_ref: str = TARGET_SECTION_REF, expected_type: str = "program_section") -> None:
    target = data.get("target")
    if not isinstance(target, dict):
        raise ValueError("Missing target object.")
    if target.get("type") != expected_type:
        raise ValueError(f"target.type must be {expected_type}.")
    ref_key = "section_ref" if expected_type == "program_section" else "commitment_ref"
    if target.get(ref_key) != expected_ref:
        raise ValueError(f"target.{ref_key} must be {expected_ref}.")


def _existing_section_refs(section: ProgramSection) -> set[str]:
    refs = {TARGET_SECTION_REF}
    for child in section.child_sections:
        if child.import_ref:
            refs.add(child.import_ref)
        refs.update(_existing_section_refs(child) - {TARGET_SECTION_REF})
    return refs


def _find_section_by_ref(db: Session, program_id: UUID, ref: str) -> ProgramSection | None:
    return db.scalar(select(ProgramSection).where(ProgramSection.program_id == program_id, ProgramSection.import_ref == ref))


def _find_commitment_by_ref(db: Session, program_id: UUID, ref: str) -> Commitment | None:
    return db.scalar(select(Commitment).where(Commitment.program_id == program_id, Commitment.import_ref == ref))


def _apply_section_fields(item: ProgramSection, section: dict[str, Any]) -> None:
    item.section_code = optional_text(section.get("section_code"))
    item.title = section["title"].strip()
    item.original_heading = optional_text(section.get("original_heading"))
    item.original_text = optional_text(section.get("original_text"))
    item.summary = optional_text(section.get("summary"))
    item.problem_description = optional_text(section.get("problem_description"))
    item.policy_area = optional_text(section.get("policy_area"))
    item.display_order = _int_or_default(section.get("display_order"), "section.display_order")
    item.source_origin = item.source_origin or "ai_imported"
    item.structural_status = "parsed"
    item.factual_review_status = item.factual_review_status or "not_reviewed"


def _apply_commitment_structure_fields(item: Commitment, program: Program, commitment: dict[str, Any], section: ProgramSection | None) -> None:
    item.program_id = program.id
    item.program_section_id = section.id if section else None
    item.display_code = optional_text(commitment.get("display_code"))
    item.title = commitment["title"].strip()
    item.original_text = optional_text(commitment.get("original_text"))
    item.normalized_description = optional_text(commitment.get("normalized_description"))
    item.political_subject_name = program.political_subject_name
    item.related_party_id = program.related_party_id
    item.related_coalition_name = program.related_coalition_name
    item.topic = optional_text(commitment.get("topic"))
    item.responsible_institutions_text = optional_text(commitment.get("responsible_institutions_text"))
    item.period_text = optional_text(commitment.get("period_text"))
    item.deadline = parse_date_or_none(commitment.get("deadline"))
    item.measurable_criteria = optional_text(commitment.get("measurable_criteria"))
    item.commitment_type = _enum_or_none(commitment.get("commitment_type"), set(COMMITMENT_TYPES), "commitment.commitment_type")
    item.promised_item_type = _enum_or_none(commitment.get("promised_item_type"), set(COMMITMENT_TYPES), "commitment.promised_item_type")
    importance_level = _enum_or_none(commitment.get("importance_level"), set(IMPORTANCE_LEVELS), "commitment.importance_level")
    if importance_level:
        item.importance_level = importance_level
    if item.importance_level not in IMPORTANCE_LEVELS:
        item.importance_level = "standard"
    item.importance_weight = IMPORTANCE_LEVELS[item.importance_level]["weight"]
    item.materiality = commitment.get("materiality") if commitment.get("materiality") in MATERIALITY_LEVELS else "medium"
    item.materiality_reason = optional_text(commitment.get("materiality_reason"))
    item.is_key_commitment = bool(item.is_key_commitment)
    item.source_origin = item.source_origin or "ai_imported"
    item.structural_status = "parsed"
    item.factual_review_status = item.factual_review_status or "not_reviewed"
    item.display_order = _int_or_default(commitment.get("display_order"), "commitment.display_order")


def import_structure(db: Session, program: Program, data: dict[str, Any], ai_run: AiRun) -> int:
    ensure_ai_run_importable(ai_run)
    current_context = ai_run_context(program, PROGRAM_STRUCTURE_TASK)
    if ai_run.input_fingerprint and ai_run.input_fingerprint != _fingerprint(
        current_context["input_snapshot"], current_context["local_ref_map"]
    ):
        raise ValueError("Program source input changed after prompt generation. Generate a new prompt.")
    sections, commitments = validate_structure_json(data)
    source = data["source_retrieval"]
    program.source_acquisition_method = source["acquisition_method"]
    program.source_coverage_status = source["coverage_status"]
    warnings = [item.strip() for item in data.get("coverage_warnings") or [] if item.strip()]
    note_parts = [item for item in [optional_text(source.get("acquisition_note")), "; ".join(warnings) or None] if item]
    program.source_acquisition_note = "\n".join(note_parts) or None
    program.source_document_complete = source.get("document_complete")
    program.supplementary_source_urls = source.get("supplementary_source_urls") or []
    if optional_text(source.get("primary_source_title")):
        program.source_title = source["primary_source_title"].strip()
    if optional_text(source.get("primary_source_url")):
        program.source_url = source["primary_source_url"].strip()
    if source_retrieval_failed(data):
        return 0
    if getattr(program, "sections", None) or getattr(program, "commitments", None):
        raise ValueError("This program already has a structure. Use section refinement or remove the draft structure explicitly before a new initial import.")
    section_by_ref: dict[str, ProgramSection] = {}
    parent_refs: dict[str, str | None] = {}
    for section in sections:
        ref = section["section_ref"]
        parent_refs[ref] = optional_text(section.get("parent_section_ref"))
        item = ProgramSection(
            program_id=program.id,
            import_ref=f"{ai_run.id}:{ref}",
            slug=ensure_unique_slug(db, ProgramSection, section.get("section_code") or section["title"]),
            source_origin="ai_imported",
            structural_status="parsed",
            factual_review_status="not_reviewed",
        )
        db.add(item)
        _apply_section_fields(item, section)
        db.flush()
        section_by_ref[ref] = item

    for ref, parent_ref in parent_refs.items():
        section_by_ref[ref].parent_section_id = section_by_ref[parent_ref].id if parent_ref else None

    for commitment in commitments:
        ref = commitment["commitment_ref"]
        section = section_by_ref.get(optional_text(commitment.get("section_ref")) or "")
        item = Commitment(
            program_id=program.id,
            import_ref=f"{ai_run.id}:{ref}",
            slug=ensure_unique_slug(db, Commitment, commitment.get("display_code") or commitment["title"]),
            current_status="not_analyzed",
            status_group="pending",
            confidence="medium",
            source_origin="ai_imported",
            structural_status="parsed",
            factual_review_status="not_reviewed",
            is_published=False,
        )
        db.add(item)
        _apply_commitment_structure_fields(item, program, commitment, section)

    db.add(
        ProgramAiExtraction(
            program_id=program.id,
            ai_run_id=ai_run.id,
            extracted_commitments_count=len(commitments),
            extraction_summary=f"Imported {len(sections)} sections and {len(commitments)} commitments.",
            validation_status="imported",
        )
    )
    return len(sections) + len(commitments)


def _mapped_entity(db: Session, ai_run: AiRun, ref: str, entity_type: str, model: type[Any]) -> Any:
    entry = (ai_run.local_ref_map or {}).get(ref)
    if not isinstance(entry, dict) or entry.get("entity_type") != entity_type or not entry.get("entity_id"):
        raise ValueError(f"Unknown or out-of-scope local ref: {ref}")
    entity = db.get(model, UUID(entry["entity_id"]))
    if not entity:
        raise ValueError(f"The entity mapped by {ref} no longer exists. Generate a new prompt.")
    captured_updated_at = entry.get("updated_at")
    current_updated_at = _snapshot_timestamp(getattr(entity, "updated_at", None))
    if captured_updated_at and current_updated_at and captured_updated_at != current_updated_at:
        raise ValueError(f"The input mapped by {ref} changed after prompt generation. Generate a new prompt.")
    return entity


def validate_section_refinement_json(data: dict[str, Any], ai_run: AiRun) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    _validate_response_meta(data, {"target", "section_structure"})
    if "target" in data:
        _validate_ref_target(data)
    structure = _structure_object(data, "section_structure")
    _reject_forbidden_structure_fields(structure, "section_structure")
    sections = structure.get("sections")
    commitments = structure.get("commitments")
    if not isinstance(sections, list) or not isinstance(commitments, list):
        raise ValueError("section_structure.sections and commitments must be lists.")
    ref_map = ai_run.local_ref_map or {}
    existing_section_refs = {ref for ref, entry in ref_map.items() if entry.get("entity_type") == "program_section"}
    existing_commitment_refs = {ref for ref, entry in ref_map.items() if entry.get("entity_type") == "commitment"}
    new_section_refs: set[str] = set()
    new_commitment_refs: set[str] = set()

    section_allowed = {
        "operation", "existing_ref", "new_ref", "parent_ref", "section_code", "title", "original_heading", "original_text",
        "summary", "problem_description", "policy_area", "display_order",
    }
    for index, item in enumerate(sections, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"section_structure.sections[{index}] must be an object.")
        _reject_unknown_keys(item, section_allowed, f"section_structure.sections[{index}]")
        operation = item.get("operation")
        if operation not in {"keep", "update", "create"}:
            raise ValueError(f"section_structure.sections[{index}].operation is invalid.")
        existing_ref = optional_text(item.get("existing_ref"))
        new_ref = optional_text(item.get("new_ref"))
        if operation in {"keep", "update"}:
            if existing_ref not in existing_section_refs or existing_ref == TARGET_SECTION_REF or new_ref:
                raise ValueError(f"Unknown existing section ref: {existing_ref}")
        else:
            if existing_ref or not new_ref or new_ref in new_section_refs or new_ref in ref_map:
                raise ValueError(f"Invalid or duplicate new section ref: {new_ref}")
            new_section_refs.add(new_ref)
        if operation != "keep" and not optional_text(item.get("title")):
            raise ValueError(f"section_structure.sections[{index}].title is required.")
        _int_or_default(item.get("display_order"), f"section_structure.sections[{index}].display_order")

    allowed_parent_refs = existing_section_refs | new_section_refs
    parent_map: dict[str, str] = {}
    for item in sections:
        if item.get("operation") == "keep":
            continue
        own_ref = optional_text(item.get("existing_ref")) or optional_text(item.get("new_ref"))
        parent_ref = optional_text(item.get("parent_ref")) or TARGET_SECTION_REF
        if parent_ref not in allowed_parent_refs or parent_ref == own_ref:
            raise ValueError(f"Invalid parent_ref for section {own_ref}: {parent_ref}")
        parent_map[own_ref] = parent_ref

    for ref in parent_map:
        seen: set[str] = set()
        current = ref
        depth = 0
        while current in parent_map:
            if current in seen:
                raise ValueError(f"Circular refinement section hierarchy involving {current}.")
            seen.add(current)
            current = parent_map[current]
            depth += 1
            if depth > MAX_SECTION_DEPTH:
                raise ValueError(f"Refinement hierarchy exceeds maximum depth {MAX_SECTION_DEPTH} at {ref}.")

    commitment_allowed = {
        "operation", "existing_ref", "new_ref", "section_ref", "display_code", "title", "original_text", "normalized_description",
        "topic", "responsible_institutions_text", "period_text", "deadline", "measurable_criteria", "commitment_type",
        "promised_item_type", "importance_level", "materiality", "materiality_reason",
        "display_order",
    }
    for index, item in enumerate(commitments, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"section_structure.commitments[{index}] must be an object.")
        _reject_unknown_keys(item, commitment_allowed, f"section_structure.commitments[{index}]")
        operation = item.get("operation")
        if operation not in {"keep", "update", "create"}:
            raise ValueError(f"section_structure.commitments[{index}].operation is invalid.")
        existing_ref = optional_text(item.get("existing_ref"))
        new_ref = optional_text(item.get("new_ref"))
        if operation in {"keep", "update"}:
            if existing_ref not in existing_commitment_refs or new_ref:
                raise ValueError(f"Unknown existing commitment ref: {existing_ref}")
        else:
            if existing_ref or not new_ref or new_ref in new_commitment_refs or new_ref in ref_map:
                raise ValueError(f"Invalid or duplicate new commitment ref: {new_ref}")
            new_commitment_refs.add(new_ref)
        if operation != "keep":
            if not optional_text(item.get("title")) or not optional_text(item.get("original_text")):
                raise ValueError(f"section_structure.commitments[{index}] requires title and original_text.")
            section_ref = optional_text(item.get("section_ref")) or TARGET_SECTION_REF
            if section_ref not in allowed_parent_refs:
                raise ValueError(f"Unknown or out-of-scope section_ref: {section_ref}")
            parse_date_or_none(item.get("deadline"))
            _enum_or_none(item.get("commitment_type"), set(COMMITMENT_TYPES), f"section_structure.commitments[{index}].commitment_type")
            _enum_or_none(item.get("promised_item_type"), set(COMMITMENT_TYPES), f"section_structure.commitments[{index}].promised_item_type")
            if operation == "create":
                _enum_required(item.get("importance_level"), set(IMPORTANCE_LEVELS), f"section_structure.commitments[{index}].importance_level")
            else:
                _enum_or_none(item.get("importance_level"), set(IMPORTANCE_LEVELS), f"section_structure.commitments[{index}].importance_level")
            _enum_or_none(item.get("materiality"), set(MATERIALITY_LEVELS), f"section_structure.commitments[{index}].materiality")
            _int_or_default(item.get("display_order"), f"section_structure.commitments[{index}].display_order")
    return sections, commitments


def import_section_refinement(db: Session, section: ProgramSection, data: dict[str, Any], ai_run: AiRun) -> int:
    ensure_ai_run_importable(ai_run)
    mapped_target = _mapped_entity(db, ai_run, TARGET_SECTION_REF, "program_section", ProgramSection)
    if mapped_target.id != section.id:
        raise ValueError("TARGET_SECTION does not map to the selected section.")
    sections, commitments = validate_section_refinement_json(data, ai_run)
    program = section.program
    section_by_ref: dict[str, ProgramSection] = {TARGET_SECTION_REF: section}
    for ref, entry in (ai_run.local_ref_map or {}).items():
        if entry.get("entity_type") == "program_section" and ref != TARGET_SECTION_REF:
            section_by_ref[ref] = _mapped_entity(db, ai_run, ref, "program_section", ProgramSection)

    for section_data in sections:
        operation = section_data["operation"]
        if operation == "keep":
            continue
        ref = optional_text(section_data.get("existing_ref")) or section_data["new_ref"]
        if operation == "update":
            item = _mapped_entity(db, ai_run, ref, "program_section", ProgramSection)
        else:
            item = ProgramSection(
                program_id=program.id,
                import_ref=f"{ai_run.id}:{ref}",
                slug=ensure_unique_slug(db, ProgramSection, section_data.get("section_code") or section_data["title"]),
                source_origin="ai_imported",
                structural_status="parsed",
                factual_review_status="not_reviewed",
            )
            db.add(item)
        _apply_section_fields(item, section_data)
        db.flush()
        section_by_ref[ref] = item
        parent_ref = optional_text(section_data.get("parent_ref")) or TARGET_SECTION_REF
        section_by_ref[ref].parent_section_id = section_by_ref[parent_ref].id

    for commitment in commitments:
        operation = commitment["operation"]
        if operation == "keep":
            continue
        ref = optional_text(commitment.get("existing_ref")) or commitment["new_ref"]
        section_ref = optional_text(commitment.get("section_ref")) or TARGET_SECTION_REF
        target_section = section_by_ref.get(section_ref)
        if not target_section:
            raise ValueError(f"Unknown section_ref for commitment {ref}: {section_ref}")
        if operation == "update":
            item = _mapped_entity(db, ai_run, ref, "commitment", Commitment)
        else:
            item = Commitment(
                program_id=program.id,
                import_ref=f"{ai_run.id}:{ref}",
                slug=ensure_unique_slug(db, Commitment, commitment.get("display_code") or commitment["title"]),
                current_status="not_analyzed",
                status_group="pending",
                confidence="medium",
                source_origin="ai_imported",
                structural_status="parsed",
                factual_review_status="not_reviewed",
                is_published=False,
            )
            db.add(item)
        _apply_commitment_structure_fields(item, program, commitment, target_section)
    return sum(item.get("operation") != "keep" for item in sections + commitments)


def _validate_sources(data: dict[str, Any], *, strict: bool = False) -> dict[str, dict[str, Any]]:
    sources = data.get("sources") or []
    if not isinstance(sources, list):
        raise ValueError("sources must be a list.")
    result: dict[str, dict[str, Any]] = {}
    for index, source in enumerate(sources, start=1):
        if not isinstance(source, dict):
            raise ValueError(f"sources[{index}] must be an object.")
        _reject_unknown_keys(
            source,
            {
                "source_ref", "title", "url", "source_type", "publisher", "published_at", "quote_or_relevant_excerpt",
                "accessed_at", "description", "reliability_level",
            },
            f"sources[{index}]",
        )
        ref = optional_text(source.get("source_ref"))
        if not ref:
            raise ValueError(f"sources[{index}].source_ref is required.")
        if ref in result:
            raise ValueError(f"Duplicate source_ref: {ref}")
        source_type = source.get("source_type") or "other"
        if source_type not in EVIDENCE_SOURCE_TYPES:
            raise ValueError(f"sources[{index}].source_type is invalid.")
        reliability = source.get("reliability_level") or "medium"
        if reliability not in CONFIDENCE_LEVELS:
            raise ValueError(f"sources[{index}].reliability_level is invalid.")
        if not optional_text(source.get("title")):
            raise ValueError(f"sources[{index}].title is required.")
        source_url = validate_url_or_none(source.get("url"), f"sources[{index}].url")
        accessed_at = parse_date_or_none(source.get("accessed_at"))
        if strict and accessed_at is None:
            raise ValueError(f"sources[{index}].accessed_at is required by schema {PROGRAM_AI_SCHEMA_VERSION}.")
        result[ref] = {
            "source_ref": ref,
            "title": source["title"].strip(),
            "url": source_url or "",
            "source_type": source_type,
            "publisher": optional_text(source.get("publisher")),
            "published_at": parse_date_or_none(source.get("published_at")),
            "accessed_at": accessed_at,
            "quote_or_relevant_excerpt": optional_text(source.get("quote_or_relevant_excerpt")),
            "description": optional_text(source.get("description")),
            "reliability_level": reliability,
        }
    return result


def _evidence_links(
    analysis: dict[str, Any],
    sources_by_ref: dict[str, dict[str, Any]],
    *,
    component_refs: set[str] | None = None,
    strict: bool = False,
) -> list[dict[str, Any]]:
    raw_links = analysis.get("evidence_links")
    raw_links = raw_links or []
    if not isinstance(raw_links, list):
        raise ValueError("evidence_links must be a list.")
    links: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str | None]] = set()
    for index, link in enumerate(raw_links, start=1):
        if not isinstance(link, dict):
            raise ValueError(f"evidence_links[{index}] must be an object.")
        source_ref = optional_text(link.get("source_ref"))
        if not source_ref:
            raise ValueError(f"evidence_links[{index}].source_ref is required.")
        if source_ref not in sources_by_ref:
            raise ValueError(f"Unknown evidence source_ref: {source_ref}")
        _reject_unknown_keys(
            link,
            {
                "source_ref", "relation_type", "evidence_role", "evidence_strength", "claim", "component_refs",
                "is_self_reported", "is_independent_confirmation", "is_contradictory", "is_disproven", "limitations",
            },
            f"evidence_links[{index}]",
        )
        relation_type = link.get("relation_type") or "supports_status"
        if relation_type not in COMMITMENT_EVIDENCE_RELATION_TYPES:
            raise ValueError(f"evidence_links[{index}].relation_type is invalid.")
        evidence_role = _enum_or_none(link.get("evidence_role"), set(EVIDENCE_ROLES), f"evidence_links[{index}].evidence_role")
        evidence_strength = _enum_or_none(
            link.get("evidence_strength"),
            set(EVIDENCE_STRENGTHS),
            f"evidence_links[{index}].evidence_strength",
        )
        claim = optional_text(link.get("claim"))
        linked_component_refs = link.get("component_refs") or []
        if not isinstance(linked_component_refs, list) or any(not isinstance(item, str) for item in linked_component_refs):
            raise ValueError(f"evidence_links[{index}].component_refs must be a list of strings.")
        if len(set(linked_component_refs)) != len(linked_component_refs):
            raise ValueError(f"evidence_links[{index}].component_refs contains duplicates.")
        unknown_component_refs = set(linked_component_refs) - (component_refs or set())
        if unknown_component_refs:
            raise ValueError(f"evidence_links[{index}] references unknown material components: {sorted(unknown_component_refs)}.")
        if strict and (not evidence_role or not evidence_strength or not claim or not linked_component_refs):
            raise ValueError(
                f"evidence_links[{index}] requires evidence_role, evidence_strength, claim, and component_refs in schema {PROGRAM_AI_SCHEMA_VERSION}."
            )
        key = (source_ref, relation_type, evidence_role)
        if key in seen:
            raise ValueError(f"Duplicate evidence link: {source_ref}/{relation_type}/{evidence_role}")
        seen.add(key)
        links.append(
            {
                "source_ref": source_ref,
                "relation_type": relation_type,
                "evidence_role": evidence_role,
                "evidence_strength": evidence_strength,
                "claim": claim,
                "component_refs": linked_component_refs,
                "is_self_reported": _bool_or_default(link.get("is_self_reported"), f"evidence_links[{index}].is_self_reported"),
                "is_independent_confirmation": _bool_or_default(
                    link.get("is_independent_confirmation"),
                    f"evidence_links[{index}].is_independent_confirmation",
                ),
                "is_contradictory": _bool_or_default(link.get("is_contradictory"), f"evidence_links[{index}].is_contradictory"),
                "is_disproven": _bool_or_default(link.get("is_disproven"), f"evidence_links[{index}].is_disproven"),
                "limitations": optional_text(link.get("limitations")),
            }
        )
    return links


def _validate_material_components(
    value: Any,
    sources_by_ref: dict[str, dict[str, Any]],
    *,
    label: str,
    strict: bool,
) -> tuple[list[dict[str, Any]], set[str]]:
    if value is None and not strict:
        return [], set()
    if not isinstance(value, list) or not value:
        raise ValueError(f"{label}.material_components must be a nonempty list.")
    result: list[dict[str, Any]] = []
    refs: set[str] = set()
    for index, component in enumerate(value, start=1):
        component_label = f"{label}.material_components[{index}]"
        if not isinstance(component, dict):
            raise ValueError(f"{component_label} must be an object.")
        _reject_unknown_keys(
            component,
            {"component_ref", "description", "promised_item_type", "status", "finding", "evidence_refs"},
            component_label,
        )
        component_ref = optional_text(component.get("component_ref"))
        if not component_ref or component_ref in refs:
            raise ValueError(f"{component_label}.component_ref must be nonempty and unique.")
        refs.add(component_ref)
        description = optional_text(component.get("description"))
        finding = optional_text(component.get("finding"))
        if not description or not finding:
            raise ValueError(f"{component_label}.description and finding are required.")
        item_type = _enum_or_none(component.get("promised_item_type"), set(COMMITMENT_TYPES), f"{component_label}.promised_item_type")
        component_status = component.get("status")
        if component_status not in MATERIAL_COMPONENT_STATUSES:
            raise ValueError(f"{component_label}.status is invalid.")
        evidence_refs = component.get("evidence_refs") or []
        if not isinstance(evidence_refs, list) or any(not isinstance(item, str) for item in evidence_refs):
            raise ValueError(f"{component_label}.evidence_refs must be a list of strings.")
        if len(set(evidence_refs)) != len(evidence_refs):
            raise ValueError(f"{component_label}.evidence_refs contains duplicates.")
        unknown_sources = set(evidence_refs) - set(sources_by_ref)
        if unknown_sources:
            raise ValueError(f"{component_label} references unknown sources: {sorted(unknown_sources)}.")
        if strict and component_status in {"complete", "in_progress"} and not evidence_refs:
            raise ValueError(f"{component_label} requires evidence_refs for status {component_status}.")
        result.append(
            {
                "component_ref": component_ref,
                "description": description,
                "promised_item_type": item_type,
                "status": component_status,
                "finding": finding,
                "evidence_refs": evidence_refs,
            }
        )
    return result, refs


def _validate_evidence_gaps(value: Any, *, label: str, strict: bool) -> list[dict[str, str]]:
    if isinstance(value, str):
        text = value.strip()
        return [{"kind": "missing", "description": text, "impact_on_conclusion": text}] if text else []
    if value is None and not strict:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{label}.missing_or_uncertain_evidence must be a list.")
    result = []
    for index, gap in enumerate(value, start=1):
        gap_label = f"{label}.missing_or_uncertain_evidence[{index}]"
        if not isinstance(gap, dict):
            raise ValueError(f"{gap_label} must be an object.")
        _reject_unknown_keys(gap, {"kind", "description", "impact_on_conclusion"}, gap_label)
        if gap.get("kind") not in EVIDENCE_GAP_KINDS:
            raise ValueError(f"{gap_label}.kind is invalid.")
        description = optional_text(gap.get("description"))
        impact = optional_text(gap.get("impact_on_conclusion"))
        if not description or not impact:
            raise ValueError(f"{gap_label}.description and impact_on_conclusion are required.")
        result.append({"kind": gap["kind"], "description": description, "impact_on_conclusion": impact})
    return result


def _validate_status_analysis(
    analysis: dict[str, Any],
    sources_by_ref: dict[str, dict[str, Any]],
    *,
    expected_refs: set[str],
    label: str = "commitment_analysis",
    strict: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(analysis, dict):
        raise ValueError(f"{label} must be an object.")
    _reject_unknown_keys(
        analysis,
        {
            "commitment_ref", "deadline", "deadline_type", "period", "conditional_trigger", "measurable_criteria",
            "commitment_type", "promised_item_type", "material_components", "baseline_mode", "baseline_explanation",
            "responsible_authority", "required_external_actors", "control_level", "control_level_explanation", "evaluation_basis", "formal_implementation_status",
            "material_implementation_status", "current_status", "status_explanation", "conclusion_basis", "confidence",
            "confidence_explanation", "missing_or_uncertain_evidence", "contribution_level", "contribution_explanation",
            "contribution_counterfactual", "contribution_confidence", "contribution_types",
            "contribution_applies_to_component_refs", "official_program_change_note", "source_version_note",
            "quantitative_target", "quantitative_actual", "quantitative_actual_as_of", "measure_validity_status",
            "evidence_links", "importance_level", "importance_weight", "status_group", "human_review_recommended",
            "human_review_reason",
        },
        label,
    )
    backend_owned = {"importance_level", "importance_weight", "status_group", "human_review_recommended", "human_review_reason"}
    supplied_backend_fields = backend_owned & set(analysis)
    if strict and supplied_backend_fields:
        raise ValueError(f"{label} contains backend-owned fields: {', '.join(sorted(supplied_backend_fields))}.")

    normalized = dict(analysis)
    commitment_ref = analysis.get("commitment_ref")
    if commitment_ref not in expected_refs:
        raise ValueError(f"{label}.commitment_ref does not match the expected commitment.")
    deadline = parse_date_or_none(analysis.get("deadline"))
    deadline_type = analysis.get("deadline_type")
    if strict and deadline_type is None:
        raise ValueError(f"{label}.deadline_type is required.")
    if deadline_type is not None and deadline_type not in DEADLINE_TYPES:
        raise ValueError(f"{label}.deadline_type is invalid.")
    if deadline and deadline_type != "explicit_date":
        raise ValueError(f"{label}.deadline_type must be explicit_date when deadline is a concrete date.")
    period = optional_text(analysis.get("period"))
    trigger = optional_text(analysis.get("conditional_trigger"))
    if deadline_type == "conditional" and not trigger:
        raise ValueError(f"{label}.conditional_trigger is required for conditional promises.")
    criteria = analysis.get("measurable_criteria") or []
    if not isinstance(criteria, list) or any(not isinstance(item, str) for item in criteria):
        raise ValueError(f"{label}.measurable_criteria must be a list of strings.")
    normalized["deadline"] = deadline.isoformat() if deadline else None
    normalized["deadline_type"] = deadline_type
    normalized["period"] = period
    normalized["conditional_trigger"] = trigger
    normalized["measurable_criteria"] = [item.strip() for item in criteria if item.strip()]
    current_status = analysis.get("current_status")
    if current_status not in IMPLEMENTATION_STATUSES:
        raise ValueError(f"{label}.current_status is invalid.")
    legacy_status_group = analysis.get("status_group")
    if legacy_status_group is not None:
        expected_group = STATUS_GROUP_BY_STATUS[current_status]
        if legacy_status_group not in ALLOWED_STATUS_GROUPS or legacy_status_group != expected_group:
            raise ValueError(f"{label}.status_group must be {expected_group} for {current_status}.")
    confidence = analysis.get("confidence")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError(f"{label}.confidence is invalid.")
    status_explanation = optional_text(analysis.get("status_explanation"))
    if not status_explanation:
        raise ValueError(f"{label}.status_explanation is required.")

    _enum_or_none(analysis.get("commitment_type"), set(COMMITMENT_TYPES), f"{label}.commitment_type")
    _enum_or_none(analysis.get("promised_item_type"), set(COMMITMENT_TYPES), f"{label}.promised_item_type")
    baseline_mode = _enum_or_none(analysis.get("baseline_mode"), set(BASELINE_MODES), f"{label}.baseline_mode")
    control_level = _enum_or_none(analysis.get("control_level"), set(CONTROL_LEVELS), f"{label}.control_level")
    _enum_or_none(analysis.get("measure_validity_status"), set(MEASURE_VALIDITY_STATUSES), f"{label}.measure_validity_status")
    if strict and (not baseline_mode or not optional_text(analysis.get("baseline_explanation"))):
        raise ValueError(f"{label}.baseline_mode and baseline_explanation are required.")
    if strict and (not control_level or not optional_text(analysis.get("control_level_explanation"))):
        raise ValueError(f"{label}.control_level and control_level_explanation are required.")
    if strict and not optional_text(analysis.get("evaluation_basis")):
        raise ValueError(f"{label}.evaluation_basis is required.")

    required_external_actors = analysis.get("required_external_actors") or []
    if not isinstance(required_external_actors, list) or any(not isinstance(item, str) for item in required_external_actors):
        raise ValueError(f"{label}.required_external_actors must be a list of strings.")
    normalized["required_external_actors"] = [item.strip() for item in required_external_actors if item.strip()]

    components, component_refs = _validate_material_components(
        analysis.get("material_components"), sources_by_ref, label=label, strict=strict
    )
    normalized["material_components"] = components

    for field_name in ("formal_implementation_status", "material_implementation_status"):
        value = analysis.get(field_name)
        if value is not None and value not in IMPLEMENTATION_DIMENSION_STATUSES:
            raise ValueError(f"{label}.{field_name} is invalid.")
        if strict and value is None:
            raise ValueError(f"{label}.{field_name} is required.")
    conclusion_basis = analysis.get("conclusion_basis")
    if conclusion_basis is not None and conclusion_basis not in CONCLUSION_BASES:
        raise ValueError(f"{label}.conclusion_basis is invalid.")
    if strict and conclusion_basis is None:
        raise ValueError(f"{label}.conclusion_basis is required.")
    confidence_explanation = optional_text(analysis.get("confidence_explanation"))
    if strict and not confidence_explanation:
        raise ValueError(f"{label}.confidence_explanation is required.")
    gaps = _validate_evidence_gaps(analysis.get("missing_or_uncertain_evidence"), label=label, strict=strict)
    normalized["missing_or_uncertain_evidence"] = gaps

    contribution_level = analysis.get("contribution_level") or DEFAULT_CONTRIBUTION_LEVEL
    if contribution_level not in CONTRIBUTION_LEVELS:
        raise ValueError(f"{label}.contribution_level is invalid.")
    contribution_explanation = optional_text(analysis.get("contribution_explanation"))
    if contribution_level != DEFAULT_CONTRIBUTION_LEVEL and not contribution_explanation:
        raise ValueError(f"{label}.contribution_explanation is required.")
    counterfactual = optional_text(analysis.get("contribution_counterfactual"))
    if strict and not counterfactual:
        raise ValueError(f"{label}.contribution_counterfactual is required.")
    if analysis.get("contribution_confidence") is not None and analysis.get("contribution_confidence") not in CONFIDENCE_LEVELS:
        raise ValueError(f"{label}.contribution_confidence is invalid.")
    if strict and analysis.get("contribution_confidence") is None:
        raise ValueError(f"{label}.contribution_confidence is required.")
    contribution_types = analysis.get("contribution_types") or []
    if not isinstance(contribution_types, list) or any(item not in CONTRIBUTION_TYPES for item in contribution_types):
        raise ValueError(f"{label}.contribution_types must be a list of valid contribution type keys.")
    applies_to = analysis.get("contribution_applies_to_component_refs") or []
    if not isinstance(applies_to, list) or any(not isinstance(item, str) for item in applies_to):
        raise ValueError(f"{label}.contribution_applies_to_component_refs must be a list of strings.")
    if set(applies_to) - component_refs:
        raise ValueError(f"{label}.contribution_applies_to_component_refs contains unknown refs.")
    if contribution_level == "decisive":
        if not counterfactual or len(counterfactual.split()) < 15:
            raise ValueError(f"{label}.decisive contribution requires a substantive counterfactual explanation.")
        if not applies_to:
            raise ValueError(f"{label}.decisive contribution must identify the material components to which it applies.")

    quantitative_actual = optional_text(analysis.get("quantitative_actual"))
    quantitative_actual_as_of = parse_date_or_none(analysis.get("quantitative_actual_as_of"))
    if quantitative_actual and not quantitative_actual_as_of:
        raise ValueError(f"{label}.quantitative_actual_as_of is required when quantitative_actual is present.")

    links = _evidence_links(
        normalized,
        sources_by_ref,
        component_refs=component_refs,
        strict=strict,
    )
    if strict and not links and current_status not in {"unclear", "not_started"}:
        raise ValueError(f"{label}.evidence_links must contain at least one claim-specific evidence link.")
    if quantitative_actual:
        linked_sources = {link["source_ref"] for link in links}
        if not any(
            sources_by_ref[ref].get("published_at") or sources_by_ref[ref].get("accessed_at")
            for ref in linked_sources
        ):
            raise ValueError(f"{label}.quantitative_actual requires a dated or access-dated linked source.")

    if current_status == "fulfilled" and any(
        component["status"] not in {"complete", "not_applicable"} for component in components
    ):
        raise ValueError(f"{label}.fulfilled is invalid while a material component is incomplete.")
    if current_status in {"not_started", "violated", "abandoned"} and conclusion_basis == "absence_of_evidence":
        raise ValueError(f"{label}.{current_status} cannot be justified only by absence of evidence; use unclear.")
    if confidence == "high" and conclusion_basis == "absence_of_evidence":
        raise ValueError(f"{label}.high confidence cannot rest primarily on missing evidence.")

    normalized["status_group"] = STATUS_GROUP_BY_STATUS[current_status]
    normalized.pop("importance_level", None)
    normalized.pop("importance_weight", None)
    normalized.pop("human_review_recommended", None)
    normalized.pop("human_review_reason", None)
    return normalized, links


def validate_status_json(data: dict[str, Any], expected_commitment_refs: set[str]) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[dict[str, Any]]]:
    strict = _validate_status_response_meta(data, {"target", "commitment_analysis", "sources"})
    expected_ref = next(iter(expected_commitment_refs)) if len(expected_commitment_refs) == 1 else TARGET_COMMITMENT_REF
    if strict or "target" in data:
        _validate_ref_target(data, expected_ref, expected_type="commitment")
    analysis = data.get("commitment_analysis")
    sources_by_ref = _validate_sources(data, strict=strict)
    analysis, links = _validate_status_analysis(
        analysis,
        sources_by_ref,
        expected_refs=expected_commitment_refs,
        strict=strict,
    )
    used_refs = {link["source_ref"] for link in links}
    if used_refs != set(sources_by_ref):
        raise ValueError("Every source must be referenced exactly by at least one evidence link.")
    return analysis, sources_by_ref, links


def _validate_analysis_date_bounds(
    analysis: dict[str, Any],
    sources_by_ref: dict[str, dict[str, Any]],
    analysis_date: date | None,
) -> None:
    if analysis_date is None:
        return
    quantitative_date = parse_date_or_none(analysis.get("quantitative_actual_as_of"))
    if quantitative_date and quantitative_date > analysis_date:
        raise ValueError("quantitative_actual_as_of cannot be later than the stored analysis date.")
    for source_ref, source in sources_by_ref.items():
        if source.get("published_at") and source["published_at"] > analysis_date:
            raise ValueError(f"Source {source_ref} was published after the stored analysis date.")
        if source.get("accessed_at") and source["accessed_at"] > analysis_date:
            raise ValueError(f"Source {source_ref} was accessed after the stored analysis date.")


def _canonical_url(url: str) -> str:
    raw = urldefrag(url.strip())[0]
    if not raw:
        return ""
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    port = parsed.port
    if port and not ((scheme == "http" and port == 80) or (scheme == "https" and port == 443)):
        hostname = f"{hostname}:{port}"
    query = urlencode(
        sorted(
            (key, value)
            for key, value in parse_qsl(parsed.query, keep_blank_values=True)
            if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
        )
    )
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit((scheme, hostname, path, query, ""))


def _create_evidence_items(db: Session, sources_by_ref: dict[str, dict[str, Any]], ai_run: AiRun, user: dict | None = None) -> dict[str, EvidenceItem]:
    evidence_by_ref = {}
    evidence_by_url: dict[str, EvidenceItem] = {}
    for ref, source in sources_by_ref.items():
        canonical_url = _canonical_url(source["url"]) if source["url"] else ""
        evidence = evidence_by_url.get(canonical_url) if canonical_url else None
        if canonical_url:
            evidence = evidence or db.scalar(select(EvidenceItem).where(func.lower(EvidenceItem.url) == canonical_url.lower()))
        if evidence:
            if source.get("accessed_at") and (not evidence.accessed_at or source["accessed_at"] > evidence.accessed_at):
                evidence.accessed_at = source["accessed_at"]
            evidence_by_ref[ref] = evidence
            evidence_by_url[canonical_url] = evidence
            continue
        evidence = EvidenceItem(
            title=source["title"],
            url=canonical_url,
            source_type=source["source_type"],
            publisher=source["publisher"],
            published_at=source["published_at"],
            accessed_at=source.get("accessed_at"),
            quote_or_relevant_excerpt=source["quote_or_relevant_excerpt"],
            description=source["description"],
            reliability_level=source["reliability_level"],
            source_origin="ai_imported",
            structural_status="parsed",
            factual_review_status="not_reviewed",
            created_from_ai_run_id=ai_run.id,
            created_by_user_id=_user_id(user),
        )
        db.add(evidence)
        db.flush()
        evidence_by_ref[ref] = evidence
        if canonical_url:
            evidence_by_url[canonical_url] = evidence
    return evidence_by_ref


def derive_human_review_reasons(
    commitment: Commitment,
    analysis: dict[str, Any],
    links: list[dict[str, Any]],
    evidence_by_ref: dict[str, EvidenceItem],
    *,
    previous_status: str | None = None,
    had_previous_analysis: bool = False,
) -> list[dict[str, str]]:
    reasons: list[dict[str, str]] = []

    def add(code: str, message: str) -> None:
        if not any(item["code"] == code for item in reasons):
            reasons.append({"code": code, "message": message})

    if analysis.get("confidence") in {"low", "medium"}:
        add("non_high_status_confidence", "Увереността в избрания статус не е висока.")
    if any(link.get("is_contradictory") or link.get("evidence_strength") == "contradictory" for link in links):
        add("contradictory_strong_evidence", "Има съществено противоречиво доказателство.")
    if analysis.get("promised_item_type") == "public_outcome" or analysis.get("commitment_type") == "public_outcome":
        add("broad_public_outcome", "Ангажиментът обещава широк обществен резултат.")
    if len(analysis.get("material_components") or []) > 1:
        add("multiple_material_components", "Ангажиментът съдържа повече от един материално различен компонент.")
    if analysis.get("conclusion_basis") == "absence_of_evidence":
        add("absence_heavy_conclusion", "Изводът зависи в голяма степен от липса на открити доказателства.")
    if analysis.get("contribution_level") == "decisive":
        add("decisive_contribution", "Оценката за приноса е решаваща и изисква човешка проверка на контрафактуалния извод.")
    if analysis.get("baseline_mode") in {None, "unclear"}:
        add("uncertain_baseline", "Изходната ситуация не е установена достатъчно сигурно.")
    if analysis.get("quantitative_actual"):
        add("dynamic_quantitative_data", "Анализът използва динамична количествена стойност, която трябва да се проверява към датата.")
    if had_previous_analysis and previous_status != analysis.get("current_status"):
        add("previous_status_disagreement", "Новият статус се различава от предходния анализ.")
    gap_kinds = {item.get("kind") for item in analysis.get("missing_or_uncertain_evidence") or []}
    if gap_kinds & {"inaccessible", "outdated", "contradictory"}:
        add("incomplete_primary_evidence", "Част от важните доказателства са недостъпни, остарели или противоречиви.")
    if links and sum(1 for link in links if link.get("is_self_reported")) * 2 > len(links):
        add("predominantly_self_reported", "Повечето доказателствени връзки са самоотчет на отговорната институция.")
    if analysis.get("formal_implementation_status") == "complete" and analysis.get("material_implementation_status") != "complete":
        add("formal_without_material_operation", "Има формално завършване без доказано пълно материално действие.")
    if links and not any(link.get("is_independent_confirmation") for link in links):
        source_types = {evidence_by_ref[link["source_ref"]].source_type for link in links}
        if source_types <= {"institutional_statement", "official_press_release", "public_statement"}:
            add("no_independent_confirmation", "Няма независимо потвърждение извън институционални съобщения.")
    return reasons


def _apply_commitment_status(
    db: Session,
    commitment: Commitment,
    analysis: dict[str, Any],
    links: list[dict[str, Any]],
    evidence_by_ref: dict[str, EvidenceItem],
    ai_run: AiRun,
    user: dict | None = None,
) -> list[dict[str, str]]:
    previous_status = commitment.current_status
    previous_group = commitment.status_group
    previous_contribution = getattr(commitment, "contribution_level", DEFAULT_CONTRIBUTION_LEVEL)
    commitment.commitment_type = _enum_or_none(analysis.get("commitment_type"), set(COMMITMENT_TYPES), "commitment_analysis.commitment_type") or commitment.commitment_type
    commitment.promised_item_type = _enum_or_none(
        analysis.get("promised_item_type"),
        set(COMMITMENT_TYPES),
        "commitment_analysis.promised_item_type",
    ) or commitment.promised_item_type
    commitment.baseline_mode = _enum_or_none(analysis.get("baseline_mode"), set(BASELINE_MODES), "commitment_analysis.baseline_mode")
    responsible_authority = optional_text(analysis.get("responsible_authority"))
    if responsible_authority:
        commitment.responsible_institutions_text = responsible_authority
    commitment.required_external_actors = _string_list_or_text(
        analysis.get("required_external_actors"),
        "commitment_analysis.required_external_actors",
    )
    commitment.control_level = _enum_or_none(analysis.get("control_level"), set(CONTROL_LEVELS), "commitment_analysis.control_level")
    commitment.evaluation_basis = optional_text(analysis.get("evaluation_basis"))
    commitment.contribution_types_text = _string_list_or_text(analysis.get("contribution_types"), "commitment_analysis.contribution_types")
    commitment.official_program_change_note = optional_text(analysis.get("official_program_change_note"))
    commitment.source_version_note = optional_text(analysis.get("source_version_note"))
    commitment.quantitative_target = optional_text(analysis.get("quantitative_target"))
    commitment.quantitative_actual = optional_text(analysis.get("quantitative_actual"))
    commitment.measure_validity_status = _enum_or_none(
        analysis.get("measure_validity_status"),
        set(MEASURE_VALIDITY_STATUSES),
        "commitment_analysis.measure_validity_status",
    )
    commitment.current_status = analysis["current_status"]
    commitment.status_group = status_group(commitment.current_status)
    commitment.status_explanation = optional_text(analysis.get("status_explanation"))
    commitment.confidence = analysis.get("confidence") or "medium"
    gap_text = "; ".join(item["description"] for item in analysis.get("missing_or_uncertain_evidence") or [])
    commitment.confidence_explanation = optional_text(analysis.get("confidence_explanation")) or gap_text or None
    commitment.contribution_level = analysis.get("contribution_level") or DEFAULT_CONTRIBUTION_LEVEL
    commitment.contribution_explanation = optional_text(analysis.get("contribution_explanation"))
    commitment.contribution_confidence = analysis.get("contribution_confidence") or None
    effective_date = ai_run.analysis_date or date.today()
    commitment.last_status_update = effective_date
    review_reasons = derive_human_review_reasons(
        commitment,
        analysis,
        links,
        evidence_by_ref,
        previous_status=previous_status,
        had_previous_analysis=bool(getattr(commitment, "status_updates", None)),
    )
    status_update = CommitmentStatusUpdate(
        commitment_id=commitment.id,
        previous_status=previous_status,
        new_status=commitment.current_status,
        previous_status_group=previous_group,
        new_status_group=commitment.status_group,
        previous_contribution_level=previous_contribution,
        new_contribution_level=commitment.contribution_level,
        status_explanation=commitment.status_explanation,
        confidence=commitment.confidence,
        confidence_explanation=commitment.confidence_explanation,
        contribution_explanation=commitment.contribution_explanation,
        contribution_confidence=commitment.contribution_confidence,
        update_reason="; ".join(item["message"] for item in review_reasons) or None,
        effective_date=effective_date,
        source_origin="ai_imported",
        ai_run_id=ai_run.id,
        changed_by_user_id=_user_id(user),
        structural_status="parsed",
        factual_review_status="not_reviewed",
    )
    db.add(status_update)
    db.flush()

    for link in links:
        db.add(
            CommitmentEvidenceLink(
                commitment_id=commitment.id,
                status_update_id=status_update.id,
                evidence_item_id=evidence_by_ref[link["source_ref"]].id,
                relation_type=link["relation_type"],
                evidence_role=link.get("evidence_role"),
                evidence_strength=link.get("evidence_strength"),
                is_self_reported=link.get("is_self_reported", False),
                is_independent_confirmation=link.get("is_independent_confirmation", False),
                is_contradictory=link.get("is_contradictory", False),
                is_disproven=link.get("is_disproven", False),
                limitations=link.get("limitations"),
                note=link.get("claim"),
                source_origin="ai_imported",
                factual_review_status="not_reviewed",
            )
        )
    return review_reasons


def _single_commitment_ref(ai_run: AiRun) -> str:
    refs = [
        ref
        for ref, entry in (ai_run.local_ref_map or {}).items()
        if entry.get("entity_type") == "commitment"
    ]
    if len(refs) != 1:
        raise ValueError("This AI run must map exactly one commitment ref.")
    return refs[0]


def import_commitment_status(
    db: Session,
    commitment: Commitment,
    data: dict[str, Any],
    ai_run: AiRun,
    user: dict | None = None,
) -> list[dict[str, str]]:
    ensure_ai_run_importable(ai_run)
    commitment_ref = _single_commitment_ref(ai_run)
    mapped = _mapped_entity(db, ai_run, commitment_ref, "commitment", Commitment)
    if mapped.id != commitment.id:
        raise ValueError(f"{commitment_ref} does not map to the selected commitment.")
    analysis, sources_by_ref, links = validate_status_json(data, {commitment_ref})
    _validate_analysis_date_bounds(analysis, sources_by_ref, ai_run.analysis_date)
    evidence_by_ref = _create_evidence_items(db, sources_by_ref, ai_run, user)
    review_reasons = _apply_commitment_status(db, commitment, analysis, links, evidence_by_ref, ai_run, user)
    ai_run.telemetry = {
        **(ai_run.telemetry or {}),
        "sources_collected": len(sources_by_ref),
        "evidence_links": len(links),
        "confidence": analysis.get("confidence"),
        "human_review_recommended": bool(review_reasons),
        "human_review_reason_codes": [item["code"] for item in review_reasons],
        "previous_status_disagreement": any(item["code"] == "previous_status_disagreement" for item in review_reasons),
    }
    return review_reasons


def _validate_section_summary(data: dict[str, Any]) -> dict[str, Any]:
    summary = data.get("section_summary")
    if summary is None:
        return {}
    if not isinstance(summary, dict):
        raise ValueError("section_summary must be an object.")
    _reject_unknown_keys(summary, {"summary", "problem_description", "aggregate_status_summary", "key_findings"}, "section_summary")
    key_findings = summary.get("key_findings") or []
    if not isinstance(key_findings, list) or any(not isinstance(item, str) for item in key_findings):
        raise ValueError("section_summary.key_findings must be a list of strings.")
    return {
        "summary": optional_text(summary.get("summary")),
        "problem_description": optional_text(summary.get("problem_description")),
        "aggregate_status_summary": optional_text(summary.get("aggregate_status_summary")),
        "key_findings": [item.strip() for item in key_findings if item.strip()],
    }


def _apply_section_summary(section: ProgramSection, summary: dict[str, Any]) -> None:
    if "summary" in summary:
        section.summary = summary["summary"]
    if "problem_description" in summary:
        section.problem_description = summary["problem_description"]
    if "aggregate_status_summary" in summary:
        section.aggregate_status_summary = summary["aggregate_status_summary"]
    if "key_findings" in summary:
        section.key_findings = summary["key_findings"]


def validate_section_batch_status_json(
    data: dict[str, Any],
    expected_commitment_refs: set[str],
) -> tuple[dict[str, Any], list[tuple[dict[str, Any], list[dict[str, str]]]], dict[str, dict[str, Any]]]:
    strict = _validate_status_response_meta(data, {"target", "section_summary", "commitment_analyses", "sources"})
    if strict and "section_summary" in data:
        raise ValueError("section_summary is generated later and must not be returned by status schema mvp-6.")
    _validate_ref_target(data)
    summary = _validate_section_summary(data)
    sources_by_ref = _validate_sources(data, strict=strict)
    analyses = data.get("commitment_analyses")
    if not isinstance(analyses, list):
        raise ValueError("commitment_analyses must be a list.")
    seen_refs = set()
    validated = []
    for index, analysis in enumerate(analyses, start=1):
        if not isinstance(analysis, dict):
            raise ValueError(f"commitment_analyses[{index}] must be an object.")
        ref = analysis.get("commitment_ref")
        if ref in seen_refs:
            raise ValueError(f"Duplicate commitment analysis ref: {ref}")
        seen_refs.add(ref)
        validated_analysis, links = _validate_status_analysis(
            analysis,
            sources_by_ref,
            expected_refs=expected_commitment_refs,
            label=f"commitment_analyses[{index}]",
            strict=strict,
        )
        validated.append((validated_analysis, links))
    if seen_refs != expected_commitment_refs:
        missing = sorted(expected_commitment_refs - seen_refs)
        unknown = sorted(seen_refs - expected_commitment_refs)
        raise ValueError(f"commitment_ref set does not match prompt scope. Missing: {missing}; unknown: {unknown}.")
    used_refs = {link["source_ref"] for _, links in validated for link in links}
    if used_refs != set(sources_by_ref):
        raise ValueError("Every batch source must be referenced by at least one commitment evidence link.")
    return summary, validated, sources_by_ref


def import_section_batch_status(
    db: Session,
    section: ProgramSection,
    data: dict[str, Any],
    ai_run: AiRun,
    user: dict | None = None,
    *,
    expected_commitment_refs: set[str] | None = None,
) -> int:
    ensure_ai_run_importable(ai_run)
    mapped_section = _mapped_entity(db, ai_run, TARGET_SECTION_REF, "program_section", ProgramSection)
    if mapped_section.id != section.id:
        raise ValueError("TARGET_SECTION does not map to the selected section.")
    commitment_map = {
        ref: _mapped_entity(db, ai_run, ref, "commitment", Commitment)
        for ref, entry in (ai_run.local_ref_map or {}).items()
        if entry.get("entity_type") == "commitment"
    }
    if not commitment_map:
        raise ValueError("This AI run has no stored commitment scope. Generate a new prompt.")
    expected_refs = expected_commitment_refs or set(commitment_map)
    unknown_refs = expected_refs - set(commitment_map)
    if unknown_refs:
        raise ValueError(f"Batch import expected refs outside the stored scope: {sorted(unknown_refs)}")
    _, analyses, sources_by_ref = validate_section_batch_status_json(data, expected_refs)
    for analysis, _ in analyses:
        _validate_analysis_date_bounds(analysis, sources_by_ref, ai_run.analysis_date)
    evidence_by_ref = _create_evidence_items(db, sources_by_ref, ai_run, user)
    for analysis, links in analyses:
        review_reasons = _apply_commitment_status(db, commitment_map[analysis["commitment_ref"]], analysis, links, evidence_by_ref, ai_run, user)
        child_run = db.scalar(
            select(AiRun).where(
                AiRun.parent_ai_run_id == ai_run.id,
                AiRun.batch_item_ref == analysis["commitment_ref"],
            )
        )
        if child_run:
            child_run.parsed_json = {"commitment_analysis": analysis}
            child_run.status = AI_RUN_IMPORTED_STATUS
            child_run.import_error = None
            child_run.imported_at = datetime.now(timezone.utc)
            child_run.telemetry = {
                **(child_run.telemetry or {}),
                "sources_collected": len(sources_by_ref),
                "evidence_links": len(links),
                "confidence": analysis.get("confidence"),
                "human_review_recommended": bool(review_reasons),
                "review_reason_codes": [item["code"] for item in review_reasons],
            }
    return len(analyses)


def validate_section_summary_json(data: dict[str, Any]) -> dict[str, Any]:
    if "commitment_analyses" in data:
        raise ValueError("section summary import must not include commitment_analyses.")
    _validate_response_meta(data, {"target", "section_summary"})
    if "target" in data:
        _validate_ref_target(data)
    if "section_summary" not in data:
        raise ValueError("Missing section_summary object.")
    return _validate_section_summary(data)


def import_section_summary(db: Session, section: ProgramSection, data: dict[str, Any], ai_run: AiRun) -> int:
    ensure_ai_run_importable(ai_run)
    mapped_section = _mapped_entity(db, ai_run, TARGET_SECTION_REF, "program_section", ProgramSection)
    if mapped_section.id != section.id:
        raise ValueError("TARGET_SECTION does not map to the selected section.")
    for ref, entry in (ai_run.local_ref_map or {}).items():
        if entry.get("entity_type") == "commitment":
            _mapped_entity(db, ai_run, ref, "commitment", Commitment)
    summary = validate_section_summary_json(data)
    _apply_section_summary(section, summary)
    section.structural_status = "parsed"
    section.factual_review_status = section.factual_review_status or "not_reviewed"
    return 1
