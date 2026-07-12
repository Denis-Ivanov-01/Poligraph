import unittest
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment, CommitmentEvidenceLink, CommitmentStatusUpdate
from app.models.evidence import EvidenceItem
from app.models.program import Program, ProgramSection
from app.services.program_ai_workflow_service import (
    COMMITMENT_STATUS_TASK,
    MODEL_OUTPUT_METADATA_BOUNDARY,
    PROGRAM_AI_PROMPT_VERSION,
    PROGRAM_AI_SCHEMA_VERSION,
    STATUS_MODEL_OUTPUT_METADATA_CONTRACT,
    TARGET_COMMITMENT_REF,
    TARGET_SECTION_REF,
    build_commitment_status_prompt,
    build_program_structure_prompt,
    build_section_batch_status_prompt,
    build_section_refinement_prompt,
    build_section_summary_prompt,
    create_or_update_ai_run,
    import_structure,
    import_commitment_status,
    import_section_batch_status,
    import_section_summary,
    mark_no_import,
    parse_json,
    section_statistics,
    validate_section_batch_status_json,
    validate_section_refinement_json,
    validate_section_summary_json,
    validate_status_json,
    validate_structure_json,
)
from app.services.program_workflow_actions import JsonImportResult, PromptResult
from app.services.commitment_analysis_methodology import (
    CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY,
    COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
    commitment_analysis_output_schema,
)
from app.services.commitment_service import commitment_importance_weight, status_group
from app.services.commitment_service import EVIDENCE_SOURCE_TYPES


def program(
    *,
    source_description=None,
    source_url=None,
    source_title=None,
    title="Program 2026",
    political_subject_name="Party",
    period_text="2026",
    program_type="election_program",
    structural_review_status="passed",
):
    return SimpleNamespace(
        id=uuid4(),
        title=title,
        program_type=program_type,
        political_subject_name=political_subject_name,
        period_text=period_text,
        period_start=None,
        period_end=None,
        publication_date=None,
        source_url=source_url,
        source_title=source_title,
        source_description=source_description,
        description=None,
        related_party_id=None,
        related_coalition_name=None,
        related_party=None,
        structural_review_status=structural_review_status,
    )


def metadata():
    return {
        "model_name": "research-model",
        "prompt_version": "mvp-5",
        "schema_version": "mvp-5",
    }


def source_retrieval(method="provided_full_text", coverage="full", document_complete=True):
    return {
        "acquisition_method": method,
        "primary_source_title": "Program",
        "primary_source_url": "https://example.test/program.pdf",
        "publisher": "Party",
        "published_at": "2026-01-01",
        "document_complete": document_complete,
        "supplementary_source_urls": [],
        "acquisition_note": None,
        "coverage_status": coverage,
    }


def structure_payload(retrieval=None):
    return {
        **metadata(),
        "source_retrieval": retrieval or source_retrieval(),
        "coverage_warnings": [],
        "program_structure": {
            "sections": [
                {"section_ref": "SEC1", "title": "Health", "display_order": 1},
                {"section_ref": "SEC2", "parent_section_ref": "SEC1", "title": "Hospitals", "display_order": 2},
            ],
            "commitments": [
                {
                    "commitment_ref": "COM1",
                    "section_ref": "SEC2",
                    "title": "Build capacity",
                    "original_text": "Build capacity",
                    "importance_level": "standard",
                    "deadline": None,
                }
            ],
        }
    }


def status_payload(commitment_ref=TARGET_COMMITMENT_REF, relation_type="contradicts_status"):
    return {
        **metadata(),
        "commitment_analysis": {
            "commitment_ref": commitment_ref,
            "current_status": "in_progress",
            "status_group": "active",
            "status_explanation": "There is evidence of work.",
            "confidence": "medium",
            "missing_or_uncertain_evidence": None,
            "human_review_recommended": False,
            "human_review_reason": None,
            "evidence_links": [{"source_ref": "E1", "relation_type": relation_type}],
        },
        "sources": [
            {
                "source_ref": "E1",
                "title": "Official update",
                "url": "https://example.test",
                "source_type": "government_document",
                "publisher": "Institution",
                "published_at": "2026-01-01",
                "reliability_level": "high",
            }
        ],
    }


def v6_status_payload(
    commitment_ref=TARGET_COMMITMENT_REF,
    *,
    current_status="in_progress",
    component_status="in_progress",
    conclusion_basis="positive_evidence",
    contribution_level="limited",
):
    return {
        "model_name": "research-model",
        "prompt_version": PROGRAM_AI_PROMPT_VERSION,
        "schema_version": PROGRAM_AI_SCHEMA_VERSION,
        "methodology_version": COMMITMENT_ANALYSIS_METHODOLOGY_VERSION,
        "target": {"type": "commitment", "commitment_ref": commitment_ref},
        "commitment_analysis": {
            "commitment_ref": commitment_ref,
            "deadline": None,
            "deadline_type": "explicit_period",
            "period": "2026",
            "conditional_trigger": None,
            "measurable_criteria": ["100 places"],
            "commitment_type": "operational_result",
            "promised_item_type": "operational_result",
            "material_components": [
                {
                    "component_ref": "C1",
                    "description": "Operational component",
                    "promised_item_type": "operational_result",
                    "status": component_status,
                    "finding": "Official records document concrete implementation work.",
                    "evidence_refs": ["E1"],
                }
            ],
            "baseline_mode": "continuation",
            "baseline_explanation": "Official records show that the underlying infrastructure predates the cabinet.",
            "responsible_authority": "Ministry",
            "required_external_actors": [],
            "control_level": "direct",
            "control_level_explanation": "The ministry controls the operational implementation steps.",
            "evaluation_basis": "The promise requires an operating result, not only an announcement.",
            "formal_implementation_status": "partial",
            "material_implementation_status": "partial",
            "current_status": current_status,
            "status_explanation": "C1 е в процес според официалния регистър.",
            "conclusion_basis": conclusion_basis,
            "confidence": "medium",
            "confidence_explanation": "The implementation action is documented, while final operation is not yet proven.",
            "missing_or_uncertain_evidence": [],
            "contribution_level": contribution_level,
            "contribution_explanation": "The cabinet took a documented implementation step but inherited the infrastructure.",
            "contribution_counterfactual": "Without the cabinet action, the inherited infrastructure would remain but the documented implementation step would probably not occur now.",
            "contribution_confidence": "medium",
            "contribution_types": ["administrative_execution", "inherited_implementation"],
            "contribution_applies_to_component_refs": ["C1"],
            "official_program_change_note": None,
            "source_version_note": "Register state checked for the analysis date.",
            "quantitative_target": None,
            "quantitative_actual": None,
            "quantitative_actual_as_of": None,
            "measure_validity_status": "active",
            "evidence_links": [
                {
                    "source_ref": "E1",
                    "relation_type": "supports_status",
                    "evidence_role": "supports_fulfillment",
                    "evidence_strength": "strong",
                    "claim": "Concrete implementation work is recorded.",
                    "component_refs": ["C1"],
                    "is_self_reported": False,
                    "is_independent_confirmation": True,
                    "is_contradictory": False,
                    "is_disproven": False,
                    "limitations": "The record does not yet prove full operation.",
                }
            ],
        },
        "sources": [
            {
                "source_ref": "E1",
                "title": "Official register",
                "url": "https://example.test/register?utm_source=test",
                "source_type": "official_register",
                "publisher": "Institution",
                "published_at": "2026-07-10",
                "accessed_at": "2026-07-12",
                "quote_or_relevant_excerpt": "Implementation step recorded.",
                "description": "Current official register entry.",
                "reliability_level": "high",
            }
        ],
    }


class FakeQuery:
    def __init__(self, result):
        self.result = result

    def filter(self, *args):
        return self

    def order_by(self, *args):
        return self

    def first(self):
        return self.result


class FakeSession:
    def __init__(self, latest=None, entities=None):
        self.latest = latest
        self.entities = entities or {}
        self.added = []
        self.flushed_section_titles = []

    def query(self, model):
        return FakeQuery(self.latest)

    def scalar(self, statement):
        return None

    def get(self, model, entity_id):
        return self.entities.get((model, entity_id))

    def add(self, item):
        self.added.append(item)

    def flush(self):
        item = self.added[-1]
        if hasattr(item, "id") and item.id is None:
            item.id = uuid4()
        if isinstance(item, ProgramSection):
            self.flushed_section_titles.append(item.title)
            if item.title is None:
                raise AssertionError("ProgramSection was flushed before required fields were populated")


class ProgramAiWorkflowServiceTests(unittest.TestCase):
    def test_importance_weight_is_derived_only_from_editorial_level(self):
        item = SimpleNamespace(importance_level="key", importance_weight=1, materiality="low")
        self.assertEqual(commitment_importance_weight(item), 3)
        item.importance_level = "technical"
        item.importance_weight = 3
        self.assertEqual(commitment_importance_weight(item), 1)
        item.importance_level = None
        self.assertEqual(commitment_importance_weight(item), 2)

    def test_status_group_mapping_is_central_and_deterministic(self):
        self.assertEqual(status_group("fulfilled"), "completed")
        self.assertEqual(status_group("violated"), "failed")
        self.assertEqual(status_group("partially_fulfilled"), "active")
        self.assertEqual(status_group("unclear"), "unclear")

    def mapped_entities(self, commitment_count=1):
        program_item = Program(
            id=uuid4(),
            title="Program",
            slug="program",
            program_type="election_program",
            status="draft",
            structural_review_status="passed",
        )
        section = ProgramSection(
            id=uuid4(),
            program=program_item,
            program_id=program_item.id,
            title="Health",
            slug="health",
            display_order=1,
            source_origin="manual",
            structural_status="draft",
            factual_review_status="not_reviewed",
        )
        commitments = []
        for index in range(commitment_count):
            commitments.append(
                Commitment(
                    id=uuid4(),
                    program=program_item,
                    program_id=program_item.id,
                    program_section=section,
                    program_section_id=section.id,
                    title=f"Commitment {index + 1}",
                    slug=f"commitment-{index + 1}",
                    original_text=f"Commitment {index + 1}",
                    current_status="not_analyzed",
                    status_group="pending",
                    confidence="medium",
                    materiality="medium",
                    source_origin="manual",
                    structural_status="draft",
                    factual_review_status="not_reviewed",
                    display_order=index + 1,
                    is_published=False,
                )
            )
        entities = {(ProgramSection, section.id): section}
        entities.update({(Commitment, item.id): item for item in commitments})
        return program_item, section, commitments, entities

    def section_fixture(self):
        program_item = program(source_url="https://example.test/program")
        program_item.updated_at = None
        section = SimpleNamespace(
            id=uuid4(),
            updated_at=None,
            section_code="1",
            title="Health",
            original_text="Health source text",
            summary="Health summary",
            display_order=1,
            created_at=None,
            program=program_item,
            child_sections=[],
            commitments=[],
        )
        commitment = SimpleNamespace(
            id=uuid4(),
            updated_at=None,
            display_code="1.1",
            title="Build capacity",
            original_text="Build capacity",
            normalized_description="Increase capacity",
            period_text="2026",
            responsible_institutions_text="Ministry",
            measurable_criteria="100 places",
            deadline=None,
            current_status="not_analyzed",
            status_group="pending",
            status_explanation=None,
            confidence="medium",
            materiality="high",
            last_status_update=None,
            display_order=1,
            created_at=None,
            evidence_links=[],
            status_updates=[],
            program=program_item,
            program_section=section,
            parent_commitment_id=None,
            parent_commitment=None,
        )
        section.commitments = [commitment]
        return section, commitment

    def test_program_prompt_with_full_text_uses_text_as_primary_source(self):
        prompt = build_program_structure_prompt(program(source_description="Full official program text"))
        self.assertIn("Primary provided full program text", prompt)
        self.assertIn("Full official program text", prompt)
        self.assertIn("This task requires web access unless full program text is provided", prompt)

    def test_program_prompt_with_source_url_opens_url_first(self):
        prompt = build_program_structure_prompt(program(source_url="https://example.test/program"))
        self.assertIn("Provided source URL:", prompt)
        self.assertIn("open it first", prompt)
        self.assertIn("search further and report that in source_retrieval", prompt)

    def test_program_prompt_without_source_url_searches_public_web(self):
        prompt = build_program_structure_prompt(program())
        self.assertIn("No source URL was provided", prompt)
        self.assertIn("Search the public web for the official program", prompt)

    def test_program_prompt_does_not_expose_program_uuid(self):
        item = program(source_url="https://example.test/program")
        prompt = build_program_structure_prompt(item)
        self.assertNotIn(str(item.id), prompt)

    def test_all_five_prompts_have_version_json_and_no_database_ids(self):
        section, commitment = self.section_fixture()
        commitment.status_updates = [SimpleNamespace()]
        prompts = [
            build_program_structure_prompt(section.program),
            build_section_refinement_prompt(section),
            build_section_summary_prompt(section),
        ]
        for prompt in prompts:
            self.assertIn(f"Prompt version: {PROGRAM_AI_PROMPT_VERSION}", prompt)
            self.assertIn(f"Schema version: {PROGRAM_AI_SCHEMA_VERSION}", prompt)
            self.assertIn(MODEL_OUTPUT_METADATA_BOUNDARY, prompt)
            self.assertIn("valid JSON object", prompt)
            self.assertNotIn(str(section.id), prompt)
            self.assertNotIn(str(commitment.id), prompt)
        status_prompt = build_commitment_status_prompt(commitment)
        self.assertIn(f"Prompt version: {PROGRAM_AI_PROMPT_VERSION}", status_prompt)
        self.assertIn(f"Schema version: {PROGRAM_AI_SCHEMA_VERSION}", status_prompt)
        self.assertIn(STATUS_MODEL_OUTPUT_METADATA_CONTRACT, status_prompt)
        self.assertNotIn(MODEL_OUTPUT_METADATA_BOUNDARY, status_prompt)
        self.assertIn("valid JSON object", status_prompt)
        self.assertNotIn(str(section.id), status_prompt)
        self.assertNotIn(str(commitment.id), status_prompt)
        batch_manifest = build_section_batch_status_prompt(section)
        self.assertIn(f"Prompt version: {PROGRAM_AI_PROMPT_VERSION}", batch_manifest)
        self.assertIn(STATUS_MODEL_OUTPUT_METADATA_CONTRACT, batch_manifest)
        self.assertNotIn(MODEL_OUTPUT_METADATA_BOUNDARY, batch_manifest)
        self.assertIn("Tranche item count", batch_manifest)
        self.assertIn("Analyze each listed commitment independently", batch_manifest)
        self.assertNotIn(str(section.id), batch_manifest)
        self.assertNotIn(str(commitment.id), batch_manifest)

    def test_workflow_json_outputs_expose_ai_run_metadata_outside_model_schema(self):
        item = program()
        ai_run = AiRun(
            id=uuid4(),
            target_type="program",
            target_id=item.id,
            task_type="program_structure_extraction",
            execution_mode="manual_external",
            status="validated",
            model_name="research-model",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            methodology_version="2026-07-12.1",
            analysis_date=date(2026, 7, 12),
            input_tokens=100,
            output_tokens=200,
            tool_call_count=3,
            prompt_text="prompt",
        )

        prompt_payload = PromptResult(item, ai_run, "prompt", "program", item.id, ai_run.task_type).to_dict()
        self.assertEqual(prompt_payload["model_name"], "research-model")
        self.assertEqual(prompt_payload["methodology_version"], "2026-07-12.1")
        self.assertEqual(prompt_payload["ai_run"]["prompt_version"], PROGRAM_AI_PROMPT_VERSION)
        self.assertEqual(prompt_payload["ai_run"]["analysis_date"], "2026-07-12")

        import_payload = JsonImportResult(True, item, ai_run, "{}", data={"ok": True}).to_dict(include_response=True)
        self.assertEqual(import_payload["model_name"], "research-model")
        self.assertEqual(import_payload["ai_run"]["input_tokens"], 100)
        self.assertEqual(import_payload["parsed_json"], {"ok": True})

    def test_status_prompts_require_primary_research_and_distinctions(self):
        section, commitment = self.section_fixture()
        for prompt in (build_commitment_status_prompt(commitment), build_section_batch_status_prompt(section)):
            self.assertIn("primary official evidence", prompt)
            self.assertIn("proposed bill", prompt)
            self.assertIn("Absence of an easily found source is not proof", prompt)
            self.assertIn("contradictory evidence", prompt)

    def test_summary_prompt_requires_completed_item_analyses(self):
        section, _ = self.section_fixture()
        with self.assertRaisesRegex(ValueError, "requires validated item-level analyses"):
            build_section_summary_prompt(section)

    def test_summary_prompt_contains_backend_counts_after_item_analysis(self):
        section, commitment = self.section_fixture()
        commitment.status_updates = [SimpleNamespace()]
        commitment.current_status = "in_progress"
        prompt = build_section_summary_prompt(section)
        self.assertIn('"analyzed_commitments": 1', prompt)
        self.assertIn('"high_materiality_commitments": 1', prompt)
        self.assertIn("hard implementation status", prompt)

    def test_structure_json_requires_source_retrieval(self):
        payload = structure_payload()
        del payload["source_retrieval"]
        with self.assertRaisesRegex(ValueError, "Missing source_retrieval"):
            validate_structure_json(payload)

    def test_structure_json_accepts_supported_source_strategies(self):
        for strategy in ("provided_url", "independent_official_source_search", "provided_url_with_additional_search"):
            payload = structure_payload(source_retrieval(method=strategy))
            sections, commitments = validate_structure_json(payload)
            self.assertEqual(len(sections), 2)
            self.assertEqual(len(commitments), 1)

    def test_structure_json_rejects_invalid_source_retrieval_values(self):
        payload = structure_payload(source_retrieval(method="guess"))
        with self.assertRaisesRegex(ValueError, "acquisition_method is invalid"):
            validate_structure_json(payload)

        payload = structure_payload(source_retrieval(coverage="guess"))
        with self.assertRaisesRegex(ValueError, "coverage_status is invalid"):
            validate_structure_json(payload)

        payload = structure_payload(source_retrieval(method="partial_source", coverage="full"))
        with self.assertRaisesRegex(ValueError, "partial_source requires"):
            validate_structure_json(payload)

    def test_failed_source_retrieval_imports_no_records_and_can_be_stored(self):
        payload = {
            **metadata(),
            "source_retrieval": source_retrieval(
                method="source_not_found",
                coverage="unknown",
                document_complete=False,
            ),
            "coverage_warnings": ["Official source unavailable"],
            "program_structure": {"sections": [], "commitments": []},
        }
        ai_run = AiRun(
            target_type="program",
            target_id=uuid4(),
            task_type="program_structure_extraction",
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
        )
        db = FakeSession()
        imported = import_structure(db, program(), payload, ai_run)
        mark_no_import(ai_run, "{}", payload, "Source retrieval failed.")
        self.assertEqual(imported, 0)
        self.assertEqual(db.added, [])
        self.assertEqual(ai_run.status, "no_import")
        self.assertEqual(ai_run.parsed_json, payload)

    def test_structure_import_populates_section_before_flush(self):
        ai_run = AiRun(
            id=uuid4(),
            target_type="program",
            target_id=uuid4(),
            task_type="program_structure_extraction",
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
        )
        db = FakeSession()
        imported = import_structure(db, program(), structure_payload(), ai_run)
        self.assertEqual(imported, 3)
        self.assertEqual(db.flushed_section_titles, ["Health", "Hospitals"])

    def test_structure_json_accepts_sections_and_commitments(self):
        sections, commitments = validate_structure_json(structure_payload())
        self.assertEqual(len(sections), 2)
        self.assertEqual(len(commitments), 1)

    def test_structure_json_rejects_hard_status_on_commitment(self):
        payload = structure_payload()
        payload["program_structure"]["commitments"][0]["current_status"] = "fulfilled"
        with self.assertRaisesRegex(ValueError, "implementation status field"):
            validate_structure_json(payload)

    def test_structure_json_rejects_hard_status_on_section(self):
        payload = structure_payload()
        payload["program_structure"]["sections"][0]["status"] = "completed"
        with self.assertRaisesRegex(ValueError, "implementation status field"):
            validate_structure_json(payload)

    def test_structure_json_rejects_missing_commitment_original_text(self):
        payload = structure_payload()
        del payload["program_structure"]["commitments"][0]["original_text"]
        with self.assertRaisesRegex(ValueError, "original_text is required"):
            validate_structure_json(payload)

    def test_structure_json_requires_ai_importance_level_and_rejects_numeric_weight(self):
        payload = structure_payload()
        del payload["program_structure"]["commitments"][0]["importance_level"]
        with self.assertRaisesRegex(ValueError, "importance_level is required"):
            validate_structure_json(payload)

        payload = structure_payload()
        payload["program_structure"]["commitments"][0]["importance_weight"] = 3
        with self.assertRaisesRegex(ValueError, "unknown keys: importance_weight"):
            validate_structure_json(payload)

    def test_structure_json_rejects_duplicate_refs(self):
        payload = structure_payload()
        payload["program_structure"]["sections"][1]["section_ref"] = "SEC1"
        with self.assertRaisesRegex(ValueError, "Duplicate section_ref"):
            validate_structure_json(payload)

    def test_structure_json_rejects_unknown_parent_ref(self):
        payload = structure_payload()
        payload["program_structure"]["sections"][1]["parent_section_ref"] = "MISSING"
        with self.assertRaisesRegex(ValueError, "Unknown parent_section_ref"):
            validate_structure_json(payload)

    def test_structure_json_rejects_self_parent_and_circular_parent(self):
        payload = structure_payload()
        payload["program_structure"]["sections"][0]["parent_section_ref"] = "SEC1"
        with self.assertRaisesRegex(ValueError, "own parent"):
            validate_structure_json(payload)

        payload = structure_payload()
        payload["program_structure"]["sections"][0]["parent_section_ref"] = "SEC2"
        payload["program_structure"]["sections"][1]["parent_section_ref"] = "SEC1"
        with self.assertRaisesRegex(ValueError, "Circular"):
            validate_structure_json(payload)

    def test_commitment_prompt_does_not_expose_uuid(self):
        commitment_id = uuid4()
        commitment = SimpleNamespace(
            id=commitment_id,
            import_ref=None,
            title="Promise",
            original_text="Promise text",
            normalized_description="Promise normalized",
            period_text=None,
            responsible_institutions_text=None,
            measurable_criteria="Metric",
            deadline=None,
            program=SimpleNamespace(title="Program"),
            program_section=SimpleNamespace(title="Section"),
        )
        prompt = build_commitment_status_prompt(commitment)
        self.assertIn(TARGET_COMMITMENT_REF, prompt)
        self.assertNotIn(str(commitment_id), prompt)

    def test_prompt_generation_does_not_overwrite_completed_ai_run(self):
        existing = AiRun(
            target_type="commitment",
            target_id=uuid4(),
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external",
            status="imported",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="old prompt",
            raw_ai_response="{}",
        )
        db = FakeSession(existing)
        ai_run = create_or_update_ai_run(db, existing.target_type, existing.target_id, existing.task_type, "new prompt")
        self.assertIsNot(ai_run, existing)
        self.assertEqual(existing.prompt_text, "old prompt")
        self.assertEqual(db.added, [ai_run])

    def test_status_json_rejects_wrong_commitment_ref(self):
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_status_json(status_payload(commitment_ref="OTHER"), {TARGET_COMMITMENT_REF})

    def test_status_json_rejects_inconsistent_status_group(self):
        payload = status_payload()
        payload["commitment_analysis"]["status_group"] = "failed"
        with self.assertRaisesRegex(ValueError, "must be active"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_status_json_validates_sources_and_preserves_relation_type(self):
        analysis, sources, links = validate_status_json(status_payload(), {TARGET_COMMITMENT_REF})
        self.assertEqual(analysis["current_status"], "in_progress")
        self.assertEqual(sources["E1"]["source_type"], "government_document")
        self.assertEqual(links[0]["relation_type"], "contradicts_status")

    def test_v6_status_contract_contains_only_analytical_fields_and_derives_status_group(self):
        payload = v6_status_payload()
        analysis, sources, links = validate_status_json(payload, {TARGET_COMMITMENT_REF})
        self.assertEqual(analysis["status_group"], "active")
        self.assertNotIn("importance_level", payload["commitment_analysis"])
        self.assertNotIn("status_group", payload["commitment_analysis"])
        self.assertEqual(analysis["material_components"][0]["component_ref"], "C1")
        self.assertEqual(analysis["deadline_type"], "explicit_period")
        self.assertEqual(analysis["measurable_criteria"], ["100 places"])
        self.assertEqual(sources["E1"]["accessed_at"].isoformat(), "2026-07-12")
        self.assertEqual(links[0]["component_refs"], ["C1"])

    def test_v6_status_requires_exact_status_metadata_and_target(self):
        payload = v6_status_payload()
        payload["schema_version"] = "mvp-6-drift"
        with self.assertRaisesRegex(ValueError, "Unsupported legacy schema_version"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

        payload = v6_status_payload()
        payload["target"]["commitment_ref"] = "OTHER"
        with self.assertRaisesRegex(ValueError, "target.commitment_ref"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

        payload = v6_status_payload()
        del payload["model_name"]
        with self.assertRaisesRegex(ValueError, "model_name is required"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_status_prompt_and_validator_use_runtime_evidence_source_types(self):
        EVIDENCE_SOURCE_TYPES["temporary_test_source"] = "Temporary test source"
        try:
            _, commitment = self.section_fixture()
            prompt = build_commitment_status_prompt(commitment)
            self.assertIn("temporary_test_source", prompt)

            payload = v6_status_payload()
            payload["sources"][0]["source_type"] = "temporary_test_source"
            _, sources, _ = validate_status_json(payload, {TARGET_COMMITMENT_REF})
            self.assertEqual(sources["E1"]["source_type"], "temporary_test_source")
        finally:
            EVIDENCE_SOURCE_TYPES.pop("temporary_test_source", None)

    def test_batch_prompt_target_matches_validator_contract(self):
        section, _ = self.section_fixture()
        prompt = build_section_batch_status_prompt(section, commitment_refs=["COM1"])
        self.assertIn('"type": "program_section"', prompt)
        self.assertIn(f'"section_ref": "{TARGET_SECTION_REF}"', prompt)
        self.assertIn('"model_name": "string"', prompt)
        self.assertIn(f'"prompt_version": "{PROGRAM_AI_PROMPT_VERSION}"', prompt)
        self.assertIn(f'"schema_version": "{PROGRAM_AI_SCHEMA_VERSION}"', prompt)
        self.assertIn(f'"methodology_version": "{COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}"', prompt)
        self.assertIn('"deadline_type"', prompt)
        self.assertIn('"measurable_criteria"', prompt)
        self.assertIn("Source refs are response-wide", prompt)

    def test_standalone_status_prompt_has_target_metadata_and_timing_contract(self):
        _, commitment = self.section_fixture()
        prompt = build_commitment_status_prompt(commitment)
        self.assertIn('"target": {', prompt)
        self.assertIn('"type": "commitment"', prompt)
        self.assertIn(f'"commitment_ref": "{TARGET_COMMITMENT_REF}"', prompt)
        self.assertIn('"model_name": "string"', prompt)
        self.assertIn(f'"prompt_version": "{PROGRAM_AI_PROMPT_VERSION}"', prompt)
        self.assertIn(f'"schema_version": "{PROGRAM_AI_SCHEMA_VERSION}"', prompt)
        self.assertIn(f'"methodology_version": "{COMMITMENT_ANALYSIS_METHODOLOGY_VERSION}"', prompt)
        self.assertIn('"deadline"', prompt)
        self.assertIn('"deadline_type"', prompt)
        self.assertIn('"period"', prompt)
        self.assertIn('"conditional_trigger"', prompt)
        self.assertIn('"measurable_criteria"', prompt)
        self.assertNotIn("Do not return prompt_version", prompt)
        self.assertNotIn("model metadata", prompt)

    def test_status_prompts_have_no_metadata_prohibition_and_unambiguous_source_scope(self):
        section, commitment = self.section_fixture()
        prompts = [build_commitment_status_prompt(commitment), build_section_batch_status_prompt(section, commitment_refs=["COM1"])]
        for prompt in prompts:
            self.assertIn("Return model_name", prompt)
            self.assertIn("Return prompt_version", prompt)
            self.assertIn("Return schema_version", prompt)
            self.assertIn("Return methodology_version", prompt)
            self.assertIn("Source refs are response-wide", prompt)
            self.assertNotIn("Temporary source refs are scoped to this commitment only", prompt)
            self.assertNotIn("Source refs are scoped to this tranche response only", prompt)
            self.assertNotIn("Do not return prompt_version", prompt)
            self.assertNotIn("Do not return schema_version", prompt)
            self.assertNotIn("Do not return methodology_version", prompt)
            self.assertNotIn("model metadata", prompt)
            self.assertNotIn("backend controls or derives those values", prompt)

    def test_standalone_and_batch_use_same_individual_commitment_analysis_contract(self):
        standalone = commitment_analysis_output_schema(TARGET_COMMITMENT_REF)["commitment_analysis"]
        batch = commitment_analysis_output_schema("COM1")["commitment_analysis"]
        standalone["commitment_ref"] = "REF"
        batch["commitment_ref"] = "REF"
        self.assertEqual(standalone, batch)
        for field in ("deadline", "deadline_type", "period", "conditional_trigger", "measurable_criteria"):
            self.assertIn(field, standalone)

    def test_status_prompts_include_explicit_consistency_rules(self):
        section, commitment = self.section_fixture()
        for prompt in (build_commitment_status_prompt(commitment), build_section_batch_status_prompt(section, commitment_refs=["COM1"])):
            self.assertIn("fulfilled cannot be returned when material_implementation_status is partial or incomplete", prompt)
            self.assertIn("partially_fulfilled must correspond to partial material implementation", prompt)
            self.assertIn("not_started cannot coexist with complete material components", prompt)
            self.assertIn("in_progress requires verified material action", prompt)
            self.assertIn("violated requires evidence of conduct directly contrary", prompt)
            self.assertIn("delayed requires evidence of postponement", prompt)
            self.assertIn("kept_to_date applies only to continuing maintenance or negative commitments", prompt)
            self.assertIn("not_due requires a future deadline", prompt)
            self.assertIn("condition_not_met requires an explicit untriggered condition", prompt)
            self.assertIn("not_applicable requires an objective reason", prompt)
            self.assertIn("measure_validity_status describes the current validity", prompt)
            self.assertIn("must tell one coherent analytical story", prompt)

    def test_status_prompt_preserves_non_government_program_ownership(self):
        section, commitment = self.section_fixture()
        section.program.program_type = "coalition_agreement"
        section.program.political_subject_name = "Coalition A"
        prompt = build_commitment_status_prompt(commitment)
        self.assertIn("coalition agreement or coalition program", prompt)
        self.assertIn("Do not upgrade this source to an official cabinet program", prompt)
        self.assertNotIn("official cabinet/government program", prompt)

    def test_status_prompt_allows_colon_text_but_rejects_contextless_and_duplicate_scopes(self):
        section, commitment = self.section_fixture()
        commitment.original_text = "Health:"
        prompt = build_commitment_status_prompt(commitment)
        self.assertIn("Original text: Health:", prompt)

        section, commitment = self.section_fixture()
        commitment.original_text = "За болниците"
        commitment.normalized_description = None
        with self.assertRaisesRegex(ValueError, "context-dependent fragment"):
            build_commitment_status_prompt(commitment)

        section, parent = self.section_fixture()
        child = SimpleNamespace(**parent.__dict__)
        child.id = uuid4()
        child.title = "Child"
        child.parent_commitment_id = parent.id
        child.parent_commitment = parent
        child.original_text = parent.original_text
        section.program.commitments = [parent, child]
        with self.assertRaisesRegex(ValueError, "duplicates its parent"):
            build_commitment_status_prompt(child)

    def test_status_prompt_allows_distinct_child_with_parent_context(self):
        section, parent = self.section_fixture()
        child = SimpleNamespace(**parent.__dict__)
        child.id = uuid4()
        child.title = "Child commitment"
        child.original_text = "Open 100 new places"
        child.normalized_description = "Open 100 new places"
        child.parent_commitment_id = parent.id
        child.parent_commitment = parent
        section.program.commitments = [parent, child]
        prompt = build_commitment_status_prompt(child)
        self.assertIn("Parent hierarchy context", prompt)
        self.assertIn("do not score parent text as this commitment", prompt)

    def test_v6_rejects_backend_owned_model_fields(self):
        payload = v6_status_payload()
        payload["commitment_analysis"]["importance_weight"] = 3
        with self.assertRaisesRegex(ValueError, "backend-owned fields"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_rejects_fulfilled_with_incomplete_material_component(self):
        payload = v6_status_payload(current_status="fulfilled", component_status="in_progress")
        with self.assertRaisesRegex(ValueError, "fulfilled is invalid"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_rejects_hard_negative_based_only_on_missing_evidence(self):
        payload = v6_status_payload(current_status="not_started", component_status="absent", conclusion_basis="absence_of_evidence")
        with self.assertRaisesRegex(ValueError, "cannot be justified only by absence"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_rejects_high_confidence_when_conclusion_is_only_missing_evidence(self):
        payload = v6_status_payload(current_status="unclear", component_status="unclear", conclusion_basis="absence_of_evidence")
        payload["commitment_analysis"]["confidence"] = "high"
        with self.assertRaisesRegex(ValueError, "high confidence cannot rest"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_requires_substantive_decisive_counterfactual_and_component_scope(self):
        payload = v6_status_payload(contribution_level="decisive")
        payload["commitment_analysis"]["contribution_counterfactual"] = "Too short."
        with self.assertRaisesRegex(ValueError, "substantive counterfactual"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_requires_date_for_dynamic_quantitative_actual(self):
        payload = v6_status_payload()
        payload["commitment_analysis"]["quantitative_actual"] = "42%"
        with self.assertRaisesRegex(ValueError, "quantitative_actual_as_of is required"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_v6_allows_unclear_and_not_started_without_evidence_links(self):
        for current_status, component_status, conclusion_basis in (
            ("unclear", "unclear", "absence_of_evidence"),
            ("not_started", "absent", "positive_evidence"),
        ):
            payload = v6_status_payload(
                current_status=current_status,
                component_status=component_status,
                conclusion_basis=conclusion_basis,
            )
            payload["commitment_analysis"]["material_components"][0]["evidence_refs"] = []
            payload["commitment_analysis"]["evidence_links"] = []
            payload["sources"] = []
            analysis, sources, links = validate_status_json(payload, {TARGET_COMMITMENT_REF})
            self.assertEqual(analysis["current_status"], current_status)
            self.assertEqual(sources, {})
            self.assertEqual(links, [])

    def test_v6_still_requires_evidence_links_for_positive_statuses(self):
        payload = v6_status_payload(current_status="in_progress", component_status="in_progress")
        payload["commitment_analysis"]["evidence_links"] = []
        with self.assertRaisesRegex(ValueError, "evidence_links must contain"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_canonical_methodology_is_identical_in_standalone_and_batch_item_prompts(self):
        section, commitment = self.section_fixture()
        standalone = build_commitment_status_prompt(commitment)
        batch_item = build_commitment_status_prompt(commitment, commitment_ref="COM1", batch_context="Item 1 of 40")
        actual_batch = build_section_batch_status_prompt(section, commitment_refs=["COM1"])
        self.assertIn(CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY, standalone)
        self.assertIn(CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY, batch_item)
        self.assertIn(CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY, actual_batch)
        self.assertNotIn("previous_analysis_summary", standalone)
        self.assertNotIn("previous_analysis_summary", batch_item)
        self.assertNotIn("section_summary", batch_item)
        self.assertNotIn("section_summary", actual_batch)

    def test_single_status_import_uses_stored_target_and_creates_history_and_evidence(self):
        _, _, commitments, entities = self.mapped_entities()
        commitment = commitments[0]
        ai_run = AiRun(
            id=uuid4(),
            target_type="commitment",
            target_id=commitment.id,
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
            local_ref_map={TARGET_COMMITMENT_REF: {"entity_type": "commitment", "entity_id": str(commitment.id), "updated_at": None}},
        )
        db = FakeSession(entities=entities)
        import_commitment_status(db, commitment, status_payload(), ai_run)
        self.assertEqual(commitment.current_status, "in_progress")
        self.assertEqual(commitment.status_group, "active")
        self.assertEqual(sum(isinstance(item, CommitmentStatusUpdate) for item in db.added), 1)
        self.assertEqual(sum(isinstance(item, EvidenceItem) for item in db.added), 1)
        links = [item for item in db.added if isinstance(item, CommitmentEvidenceLink)]
        self.assertEqual(links[0].relation_type, "contradicts_status")

    def test_v6_import_preserves_editorial_importance_without_prompt_only_columns(self):
        _, _, commitments, entities = self.mapped_entities()
        commitment = commitments[0]
        commitment.importance_level = "key"
        commitment.importance_weight = 3
        ai_run = AiRun(
            id=uuid4(),
            target_type="commitment",
            target_id=commitment.id,
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
            local_ref_map={TARGET_COMMITMENT_REF: {"entity_type": "commitment", "entity_id": str(commitment.id), "updated_at": None}},
        )
        db = FakeSession(entities=entities)
        import_commitment_status(db, commitment, v6_status_payload(), ai_run)
        self.assertEqual(commitment.importance_level, "key")
        self.assertEqual(commitment.importance_weight, 3)
        self.assertEqual(commitment.baseline_mode, "continuation")
        self.assertFalse(hasattr(commitment, "material_components"))
        self.assertFalse(hasattr(commitment, "analysis_quality_flags"))

    def test_single_status_import_rejects_stale_target(self):
        _, _, commitments, entities = self.mapped_entities()
        commitment = commitments[0]
        commitment.updated_at = SimpleNamespace(isoformat=lambda: "new")
        ai_run = AiRun(
            target_type="commitment",
            target_id=commitment.id,
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
            local_ref_map={TARGET_COMMITMENT_REF: {"entity_type": "commitment", "entity_id": str(commitment.id), "updated_at": "old"}},
        )
        with self.assertRaisesRegex(ValueError, "changed after prompt generation"):
            import_commitment_status(FakeSession(entities=entities), commitment, status_payload(), ai_run)

    def test_batch_import_updates_every_mapped_commitment_once(self):
        _, section, commitments, entities = self.mapped_entities(commitment_count=2)
        refs = {
            TARGET_SECTION_REF: {"entity_type": "program_section", "entity_id": str(section.id), "updated_at": None},
            "COM1": {"entity_type": "commitment", "entity_id": str(commitments[0].id), "updated_at": None},
            "COM2": {"entity_type": "commitment", "entity_id": str(commitments[1].id), "updated_at": None},
        }
        ai_run = AiRun(
            id=uuid4(), target_type="program_section", target_id=section.id, task_type="program_section_commitment_status_batch_analysis",
            execution_mode="manual_external", status="prompt_generated", prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION, prompt_text="prompt", local_ref_map=refs,
        )
        first = status_payload(commitment_ref="COM1")["commitment_analysis"]
        second = status_payload(commitment_ref="COM2")["commitment_analysis"]
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "section_summary": {"summary": "Summary", "problem_description": None, "aggregate_status_summary": None, "key_findings": []},
            "commitment_analyses": [first, second],
            "sources": status_payload()["sources"],
        }
        db = FakeSession(entities=entities)
        imported = import_section_batch_status(db, section, payload, ai_run)
        self.assertEqual(imported, 2)
        self.assertEqual([item.current_status for item in commitments], ["in_progress", "in_progress"])
        self.assertEqual(sum(isinstance(item, CommitmentStatusUpdate) for item in db.added), 2)

    def test_batch_import_records_review_recommendation_in_child_telemetry(self):
        _, section, commitments, entities = self.mapped_entities(commitment_count=1)
        batch_id = uuid4()
        child = AiRun(
            id=uuid4(),
            target_type="commitment",
            target_id=commitments[0].id,
            task_type=COMMITMENT_STATUS_TASK,
            execution_mode="manual_external_batch_item",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="child prompt",
            parent_ai_run_id=batch_id,
            batch_item_ref="COM1",
        )
        ai_run = AiRun(
            id=batch_id,
            target_type="program_section",
            target_id=section.id,
            task_type="program_section_commitment_status_batch_analysis",
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
            local_ref_map={
                TARGET_SECTION_REF: {"entity_type": "program_section", "entity_id": str(section.id), "updated_at": None},
                "COM1": {"entity_type": "commitment", "entity_id": str(commitments[0].id), "updated_at": None},
            },
        )
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "commitment_analyses": [status_payload(commitment_ref="COM1")["commitment_analysis"]],
            "sources": status_payload()["sources"],
        }

        class BatchImportSession(FakeSession):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.scalar_calls = 0

            def scalar(self, statement):
                self.scalar_calls += 1
                return child if self.scalar_calls > 1 else None

        import_section_batch_status(BatchImportSession(entities=entities), section, payload, ai_run)
        self.assertTrue(child.telemetry["human_review_recommended"])
        self.assertIn("non_high_status_confidence", child.telemetry["review_reason_codes"])

    def test_summary_import_never_changes_commitment_statuses(self):
        _, section, commitments, entities = self.mapped_entities()
        ai_run = AiRun(
            target_type="program_section", target_id=section.id, task_type="program_section_summary_analysis",
            execution_mode="manual_external", status="prompt_generated", prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION, prompt_text="prompt",
            local_ref_map={
                TARGET_SECTION_REF: {"entity_type": "program_section", "entity_id": str(section.id), "updated_at": None},
                "COM1": {"entity_type": "commitment", "entity_id": str(commitments[0].id), "updated_at": None},
            },
        )
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "section_summary": {"summary": "New summary", "problem_description": "Problem", "aggregate_status_summary": "Narrative", "key_findings": ["A"]},
        }
        import_section_summary(FakeSession(entities=entities), section, payload, ai_run)
        self.assertEqual(section.summary, "New summary")
        self.assertEqual(commitments[0].current_status, "not_analyzed")

    def test_status_json_rejects_malformed_source_object(self):
        payload = status_payload()
        payload["sources"][0]["source_type"] = "blog"
        with self.assertRaisesRegex(ValueError, "source_type is invalid"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

        payload = status_payload()
        payload["sources"][0]["publisher"] = 42
        with self.assertRaisesRegex(ValueError, "Expected a string or null"):
            validate_status_json(payload, {TARGET_COMMITMENT_REF})

    def test_section_batch_rejects_unknown_commitment_ref(self):
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "commitment_analyses": [status_payload(commitment_ref="COM9")["commitment_analysis"]],
            "sources": status_payload()["sources"],
        }
        with self.assertRaisesRegex(ValueError, "does not match"):
            validate_section_batch_status_json(payload, {"COM1"})

    def test_section_batch_requires_every_selected_ref_exactly_once(self):
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "section_summary": {"summary": None, "problem_description": None, "aggregate_status_summary": None, "key_findings": []},
            "commitment_analyses": [status_payload(commitment_ref="COM1")["commitment_analysis"]],
            "sources": status_payload()["sources"],
        }
        with self.assertRaisesRegex(ValueError, "does not match prompt scope"):
            validate_section_batch_status_json(payload, {"COM1", "COM2"})

    def test_refinement_uses_explicit_operations_and_scoped_refs(self):
        section, commitment = self.section_fixture()
        ai_run = AiRun(
            task_type="program_section_structure_refinement",
            target_type="program_section",
            target_id=section.id,
            execution_mode="manual_external",
            status="prompt_generated",
            prompt_version=PROGRAM_AI_PROMPT_VERSION,
            schema_version=PROGRAM_AI_SCHEMA_VERSION,
            prompt_text="prompt",
            local_ref_map={
                TARGET_SECTION_REF: {"entity_type": "program_section", "entity_id": str(section.id), "updated_at": None},
                "EXISTING_COMMITMENT_1": {"entity_type": "commitment", "entity_id": str(commitment.id), "updated_at": None},
            },
        )
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "section_structure": {
                "sections": [],
                "commitments": [
                    {
                        "operation": "update",
                        "existing_ref": "EXISTING_COMMITMENT_1",
                        "new_ref": None,
                        "section_ref": TARGET_SECTION_REF,
                        "title": "Updated",
                        "original_text": "Updated source",
                        "display_order": 1,
                    }
                ],
            },
        }
        sections, commitments = validate_section_refinement_json(payload, ai_run)
        self.assertEqual(sections, [])
        self.assertEqual(commitments[0]["operation"], "update")

        payload["section_structure"]["commitments"][0]["existing_ref"] = "OUTSIDE_SCOPE"
        with self.assertRaisesRegex(ValueError, "Unknown existing commitment ref"):
            validate_section_refinement_json(payload, ai_run)

    def test_section_statistics_distinguishes_not_analyzed_from_unclear(self):
        section, commitment = self.section_fixture()
        commitment_2 = SimpleNamespace(**commitment.__dict__)
        commitment_2.id = uuid4()
        commitment_2.current_status = "unclear"
        commitment_2.last_status_update = None
        commitment_2.status_updates = [SimpleNamespace()]
        section.commitments = [commitment, commitment_2]
        result = section_statistics(section)
        self.assertEqual(result["not_analyzed_commitments"], 1)
        self.assertEqual(result["counts_by_status"]["unclear"], 1)

    def test_section_summary_import_shape_updates_summary_only(self):
        payload = {
            **metadata(),
            "target": {"type": "program_section", "section_ref": TARGET_SECTION_REF},
            "section_summary": {"summary": "Summary", "problem_description": None, "aggregate_status_summary": None, "key_findings": ["A"]},
        }
        summary = validate_section_summary_json(payload)
        self.assertEqual(summary["summary"], "Summary")

        payload["commitment_analyses"] = []
        with self.assertRaisesRegex(ValueError, "must not include commitment_analyses"):
            validate_section_summary_json(payload)

    def test_invalid_json_reports_clean_position(self):
        with self.assertRaisesRegex(ValueError, "Invalid JSON at line"):
            parse_json('{"broken": ')


if __name__ == "__main__":
    unittest.main()
