from datetime import datetime, timezone
from uuid import uuid4

from app.models.ai_analysis import AiRun
from app.models.commitment import Commitment
from app.models.program import Program, ProgramSection
from app.services.commitment_analysis_methodology import CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY, DEFAULT_BATCH_TRANCHE_SIZE
from app.services.program_analysis_batch_service import create_section_analysis_batch, refresh_batch_progress


class BatchSession:
    def __init__(self):
        self.added = []

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if hasattr(item, "id") and item.id is None:
                item.id = uuid4()

    def scalars(self, statement):
        return [item for item in self.added if isinstance(item, AiRun) and item.parent_ai_run_id is not None]


def section_with_commitments(count: int) -> ProgramSection:
    program = Program(
        id=uuid4(),
        title="Program",
        slug="program",
        program_type="government_program",
        political_subject_name="Cabinet",
        status="draft",
        source_url="https://example.test/program",
        structural_review_status="passed",
    )
    section = ProgramSection(
        id=uuid4(),
        program=program,
        program_id=program.id,
        title="Section",
        slug="section",
        section_code="1",
        display_order=1,
        child_sections=[],
    )
    section.commitments = [
        Commitment(
            id=uuid4(),
            program=program,
            program_id=program.id,
            program_section=section,
            program_section_id=section.id,
            title=f"Commitment {index}",
            slug=f"commitment-{index}",
            original_text=f"Promise {index}",
            normalized_description=f"Promise {index}",
            parent_commitment_id=None,
            importance_level="standard",
            importance_weight=2,
            display_order=index,
            created_at=datetime.now(timezone.utc),
        )
        for index in range(1, count + 1)
    ]
    return section


def test_batch_creates_one_canonical_scoped_child_run_per_commitment_for_first_tranche():
    db = BatchSession()
    section = section_with_commitments(DEFAULT_BATCH_TRANCHE_SIZE)
    batch = create_section_analysis_batch(db, section)
    children = [item for item in db.added if isinstance(item, AiRun) and item.parent_ai_run_id == batch.id]

    assert batch.expected_item_count == DEFAULT_BATCH_TRANCHE_SIZE
    assert len(children) == DEFAULT_BATCH_TRANCHE_SIZE
    assert [item.batch_item_ref for item in children] == [f"COM{index}" for index in range(1, 51)]
    assert all(len(item.local_ref_map) == 1 for item in children)
    assert all(CANONICAL_COMMITMENT_ANALYSIS_METHODOLOGY in item.prompt_text for item in children)
    assert all("previous_analysis_summary" not in item.prompt_text for item in children)
    assert all("section_summary" not in item.prompt_text for item in children)


def test_batch_allows_more_than_50_and_uses_50_only_as_tranche_size():
    db = BatchSession()
    section = section_with_commitments(DEFAULT_BATCH_TRANCHE_SIZE + 1)
    batch = create_section_analysis_batch(db, section)
    children = [item for item in db.added if isinstance(item, AiRun) and item.parent_ai_run_id == batch.id]

    assert batch.expected_item_count == DEFAULT_BATCH_TRANCHE_SIZE + 1
    assert len(children) == DEFAULT_BATCH_TRANCHE_SIZE + 1
    assert [item.batch_item_ref for item in children][-1] == "COM51"
    assert "Expected commitment refs in this tranche" in batch.prompt_text
    assert "COM50" in batch.prompt_text
    assert "COM51" not in batch.prompt_text


def test_batch_tranche_size_is_configurable_without_changing_parent_scope():
    db = BatchSession()
    section = section_with_commitments(12)
    batch = create_section_analysis_batch(db, section, tranche_size=5)
    children = [item for item in db.added if isinstance(item, AiRun) and item.parent_ai_run_id == batch.id]

    assert batch.expected_item_count == 12
    assert len(children) == 12
    assert batch.input_snapshot["tranche_size"] == 5
    assert batch.input_snapshot["current_tranche_refs"] == ["COM1", "COM2", "COM3", "COM4", "COM5"]
    assert "COM5" in batch.prompt_text
    assert "COM6" not in batch.prompt_text


def test_batch_progress_preserves_partial_results_and_requires_all_items_for_summary():
    db = BatchSession()
    batch = create_section_analysis_batch(db, section_with_commitments(3))
    children = [item for item in db.added if isinstance(item, AiRun) and item.parent_ai_run_id == batch.id]
    children[0].status = "imported"
    children[0].telemetry = {"confidence": "high", "sources_collected": 2, "human_review_recommended": False}
    children[1].status = "import_failed"
    children[1].retry_count = 1
    children[1].validation_errors = [{"message": "invalid"}]

    progress = refresh_batch_progress(db, batch)
    assert progress["status"] == "needs_attention"
    assert progress["execution_mode"] == "manual_external_item_batch"
    assert progress["model_name"] is None
    assert progress["methodology_version"] == batch.methodology_version
    assert progress["completed_item_count"] == 1
    assert progress["failed_item_count"] == 1
    assert progress["pending_item_count"] == 1
    assert progress["summary_ready"] is False

    for child in children:
        child.status = "imported"
        child.telemetry = {"confidence": "medium", "sources_collected": 1, "review_reason_codes": ["non_high_status_confidence"]}
    progress = refresh_batch_progress(db, batch)
    assert progress["status"] == "completed"
    assert progress["completed_item_count"] == 3
    assert progress["summary_ready"] is True
    assert progress["human_review_item_count"] == 3
