import json
import re
from datetime import date
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.commitment import Commitment, CommitmentEvidence
from app.models.program import Program
from app.resources import resource_text
from app.services.program_prompt_template import (
    PROGRAM_COMMITMENT_EXTRACTION_PROMPT_TEMPLATE,
    PROGRAM_COMMITMENT_JSON_SCHEMA,
    PROGRAM_COMMITMENT_PROMPT_VERSION,
    PROGRAM_COMMITMENT_SCHEMA_VERSION,
)

PROGRAM_TYPES = {
    "election_program": "Предизборна програма",
    "government_program": "Управленска програма",
    "coalition_agreement": "Коалиционно споразумение",
    "sector_program": "Секторна програма",
    "other": "Друго",
}

COMMITMENT_STATUSES = {
    "not_started": {
        "label": "Не започнато",
        "group": "active",
        "description": "Има заявен ангажимент, но няма видими публични действия по него.",
    },
    "in_progress": {
        "label": "В процес",
        "group": "active",
        "description": "Има реални действия, но няма завършен резултат.",
    },
    "partially_fulfilled": {
        "label": "Частично изпълнено",
        "group": "active",
        "description": "Има постигнат резултат, но той не покрива изцяло обещанието.",
    },
    "fulfilled": {
        "label": "Изпълнено",
        "group": "completed",
        "description": "Обещаното е постигнато по същество.",
    },
    "broken": {
        "label": "Нарушено",
        "group": "completed",
        "description": "Направено е обратното на заявения ангажимент.",
    },
    "abandoned": {
        "label": "Изоставено",
        "group": "completed",
        "description": "Ангажиментът вече не се преследва или е публично изоставен.",
    },
    "blocked": {
        "label": "Блокирано",
        "group": "active",
        "description": "Има действия, но изпълнението е спряно от външен фактор.",
    },
    "insufficient_data": {
        "label": "Няма достатъчно данни",
        "group": "unclear",
        "description": "Няма достатъчно надеждна публична информация за честна оценка.",
    },
}

STATUS_GROUPS = {
    "active": "Активни",
    "completed": "Завършени",
    "unclear": "Неясни",
}

CONFIDENCE_LEVELS = {
    "high": "Висока увереност",
    "medium": "Средна увереност",
    "low": "Ниска увереност",
    "insufficient_data": "Недостатъчно данни",
}

EVIDENCE_SOURCE_TYPES = {
    "bill": "Законопроект",
    "vote": "Гласуване",
    "council_of_ministers_decision": "Решение на Министерски съвет",
    "national_assembly_decision": "Решение на Народното събрание",
    "budget_change": "Бюджетна промяна",
    "public_procurement": "Обществена поръчка",
    "contract": "Договор",
    "report": "Доклад",
    "strategy": "Стратегия",
    "action_plan": "План за действие",
    "parliamentary_question": "Парламентарен въпрос",
    "transcript": "Стенограма",
    "official_press_release": "Официално прессъобщение",
    "court_act": "Съдебен акт",
    "regulatory_decision": "Регулаторно решение",
    "public_statement": "Публично изказване",
    "media_publication": "Медийна публикация",
    "other": "Друго",
}

def slugify(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", value.strip().lower()).strip("-")
    return normalized or "item"


def ensure_unique_slug(db: Session, model: type[Program] | type[Commitment], base: str, current_id: Any | None = None) -> str:
    base_slug = slugify(base)
    slug = base_slug
    counter = 2
    while True:
        query = select(model).where(model.slug == slug)
        if current_id:
            query = query.where(model.id != current_id)
        if not db.scalar(query):
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def status_group(status: str) -> str:
    return COMMITMENT_STATUSES.get(status, COMMITMENT_STATUSES["not_started"])["group"]


def unset_other_active_programs(db: Session, program: Program | None = None) -> None:
    query = select(Program).where(Program.is_active_government_program.is_(True), Program.is_deleted.is_(False))
    if program and program.id:
        query = query.where(Program.id != program.id)
    for item in db.scalars(query):
        item.is_active_government_program = False


def program_payload(program: Program) -> dict[str, Any]:
    return {
        "id": program.id,
        "title": program.title,
        "slug": program.slug,
        "description": program.description,
        "program_type": program.program_type,
        "program_type_label": PROGRAM_TYPES.get(program.program_type, program.program_type),
        "political_subject_name": program.political_subject_name,
        "related_party": {
            "id": program.related_party.id,
            "slug": program.related_party.slug,
            "full_name": program.related_party.full_name,
            "short_name": program.related_party.short_name,
        }
        if program.related_party
        else None,
        "related_coalition_name": program.related_coalition_name,
        "period_start": program.period_start,
        "period_end": program.period_end,
        "source_url": program.source_url,
        "source_title": program.source_title,
        "source_description": program.source_description,
        "is_active_government_program": program.is_active_government_program,
    }


def evidence_payload(evidence: CommitmentEvidence) -> dict[str, Any]:
    return {
        "id": evidence.id,
        "title": evidence.title,
        "url": evidence.url,
        "source_type": evidence.source_type,
        "source_type_label": EVIDENCE_SOURCE_TYPES.get(evidence.source_type, evidence.source_type),
        "publisher": evidence.publisher,
        "published_at": evidence.published_at,
        "quote_or_relevant_excerpt": evidence.quote_or_relevant_excerpt,
        "description": evidence.description,
        "supports_status": evidence.supports_status,
    }


def commitment_payload(commitment: Commitment, include_evidence: bool = False) -> dict[str, Any]:
    payload = {
        "id": commitment.id,
        "title": commitment.title,
        "slug": commitment.slug,
        "original_text": commitment.original_text if include_evidence else None,
        "normalized_description": commitment.normalized_description,
        "topic": commitment.topic,
        "responsible_institutions": commitment.responsible_institutions,
        "period": commitment.period,
        "deadline": commitment.deadline,
        "measurable_criteria": commitment.measurable_criteria,
        "status": commitment.status,
        "status_label": COMMITMENT_STATUSES.get(commitment.status, COMMITMENT_STATUSES["not_started"])["label"],
        "status_group": commitment.status_group,
        "status_group_label": STATUS_GROUPS.get(commitment.status_group, commitment.status_group),
        "status_explanation": commitment.status_explanation,
        "confidence_level": commitment.confidence_level,
        "confidence_label": CONFIDENCE_LEVELS.get(commitment.confidence_level, commitment.confidence_level),
        "confidence_explanation": commitment.confidence_explanation,
        "last_status_update": commitment.last_status_update,
        "is_key_commitment": commitment.is_key_commitment,
        "display_order": commitment.display_order,
        "program": program_payload(commitment.program),
        "evidence_count": len(commitment.evidence),
    }
    if include_evidence:
        payload["evidence"] = [evidence_payload(item) for item in commitment.evidence]
    return payload


def commitment_query():
    return select(Commitment).options(
        selectinload(Commitment.program).selectinload(Program.related_party),
        selectinload(Commitment.related_party),
        selectinload(Commitment.evidence_links).selectinload(CommitmentEvidence.evidence_item),
    )


def active_government_program_summary(db: Session) -> dict[str, Any] | None:
    program = db.scalar(
        select(Program)
        .where(Program.is_active_government_program.is_(True), Program.is_published.is_(True), Program.is_deleted.is_(False))
        .options(selectinload(Program.related_party))
    )
    if not program:
        return None
    commitments = list(
        db.scalars(
            commitment_query()
            .where(Commitment.program_id == program.id, Commitment.is_published.is_(True))
            .order_by(Commitment.display_order, Commitment.created_at)
        )
    )
    counts = {key: 0 for key in COMMITMENT_STATUSES}
    for commitment in commitments:
        counts[commitment.status] = counts.get(commitment.status, 0) + 1
    key_commitments = [item for item in commitments if item.is_key_commitment][:5]
    return {
        "program": program_payload(program),
        "total_commitments": len(commitments),
        "status_counts": counts,
        "key_commitments": [commitment_payload(item) for item in key_commitments],
    }


def topic_options(db: Session) -> list[str]:
    return [
        item
        for item in db.scalars(
            select(Commitment.topic)
            .join(Program)
            .where(Commitment.topic.is_not(None), Commitment.is_published.is_(True), Program.is_deleted.is_(False))
            .group_by(Commitment.topic)
            .order_by(Commitment.topic)
        )
        if item
    ]


def program_status_counts(db: Session, program_id) -> dict[str, int]:
    rows = db.execute(
        select(Commitment.status, func.count(Commitment.id))
        .join(Program)
        .where(
            Commitment.program_id == program_id,
            Commitment.is_published.is_(True),
            Program.is_published.is_(True),
            Program.is_deleted.is_(False),
        )
        .group_by(Commitment.status)
    ).all()
    counts = {key: 0 for key in COMMITMENT_STATUSES}
    counts.update({status: count for status, count in rows})
    return counts


def build_commitment_extraction_prompt(
    program_url: str | None,
    program_text: str | None,
    political_subject_name: str | None,
    program_type: str | None,
    period: str | None,
    notes: str | None,
) -> str:
    return PROGRAM_COMMITMENT_EXTRACTION_PROMPT_TEMPLATE.format(
        language=resource_text("language", "Bulgarian"),
        prompt_version=PROGRAM_COMMITMENT_PROMPT_VERSION,
        schema_version=PROGRAM_COMMITMENT_SCHEMA_VERSION,
        response_json_schema=PROGRAM_COMMITMENT_JSON_SCHEMA,
        program_url=program_url or "none",
        program_text=program_text
        or "If a URL is provided, use it as the source for research. If the URL cannot be accessed, return a warning.",
        political_subject_name=political_subject_name or "not specified",
        program_type=program_type or "other",
        period=period or "not specified",
        notes=notes or "none",
    )

def validate_import_json(raw_json: str) -> dict[str, Any]:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON: {exc.msg}") from exc
    if not isinstance(data, dict):
        raise ValueError("Top-level JSON must be an object.")
    program = data.get("program")
    commitments = data.get("commitments")
    if not isinstance(program, dict):
        raise ValueError("Missing program object.")
    if not isinstance(commitments, list) or not commitments:
        raise ValueError("Missing commitments array.")
    if not optional_text(program.get("title")):
        raise ValueError("program.title is required.")
    if program.get("program_type") not in PROGRAM_TYPES:
        raise ValueError("program.program_type is invalid.")
    for index, commitment in enumerate(commitments, start=1):
        if not isinstance(commitment, dict):
            raise ValueError(f"commitments[{index}] must be an object.")
        if not optional_text(commitment.get("title")):
            raise ValueError(f"commitments[{index}].title is required.")
        if not optional_text(commitment.get("original_text")):
            raise ValueError(f"commitments[{index}].original_text is required.")
        if commitment.get("initial_status", "not_started") not in COMMITMENT_STATUSES:
            raise ValueError(f"commitments[{index}].initial_status is invalid.")
        if commitment.get("confidence_level", "medium") not in CONFIDENCE_LEVELS:
            raise ValueError(f"commitments[{index}].confidence_level is invalid.")
    return data


