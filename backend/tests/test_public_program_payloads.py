from types import SimpleNamespace
from datetime import date, datetime
from uuid import uuid4

from app.services.commitment_service import (
    commitment_payload,
    public_commitment_row_payload,
    rollup_section_status_counts,
    section_summary_payload,
    zero_status_counts,
)


def section(section_id=None, parent_section_id=None, display_order=1):
    return SimpleNamespace(
        id=section_id or uuid4(),
        parent_section_id=parent_section_id,
        section_code=str(display_order),
        title=f"Section {display_order}",
        summary="Short summary",
        policy_area="policy",
        display_order=display_order,
    )


def program():
    return SimpleNamespace(
        id=uuid4(),
        title="Program",
        slug="program",
        description=None,
        short_description=None,
        program_type="government_program",
        political_subject_name="Cabinet",
        related_party=None,
        related_coalition_name=None,
        period_text="2026",
        period_start=None,
        period_end=None,
        publication_date=None,
        source_url=None,
        source_title=None,
        source_description=None,
        source_acquisition_method=None,
        source_coverage_status=None,
        source_acquisition_note=None,
        source_document_complete=True,
        supplementary_source_urls=[],
        is_active_government_program=True,
    )


def test_section_status_counts_roll_up_without_commitment_objects():
    root = section(display_order=1)
    child = section(parent_section_id=root.id, display_order=2)
    root_counts = zero_status_counts()
    root_counts["fulfilled"] = 1
    child_counts = zero_status_counts()
    child_counts["in_progress"] = 2

    result = rollup_section_status_counts([root, child], {root.id: root_counts, child.id: child_counts})

    assert result[root.id]["fulfilled"] == 1
    assert result[root.id]["in_progress"] == 2
    assert result[child.id]["in_progress"] == 2


def test_section_summary_payload_excludes_full_subsections_and_commitments():
    item = section()
    counts = zero_status_counts()
    counts["not_analyzed"] = 3

    payload = section_summary_payload(item, status_counts=counts, direct_commitment_count=1, child_section_count=2)

    assert payload["commitment_count"] == 3
    assert payload["direct_commitment_count"] == 1
    assert payload["has_subsections"] is True
    assert "commitments" not in payload
    assert "children" not in payload
    assert "original_text" not in payload


def test_public_commitment_row_payload_is_compact():
    row = SimpleNamespace(
        id=uuid4(),
        program_section_id=uuid4(),
        display_code="1.1",
        title="Build hospitals",
        slug="build-hospitals",
        normalized_description="Build hospitals in underserved regions.",
        display_order=1,
        last_status_update=None,
        status="not_analyzed",
        confidence_level=None,
        evidence_count=0,
    )

    payload = public_commitment_row_payload(row, program())

    assert payload["slug"] == "build-hospitals"
    assert payload["status"] == "not_analyzed"
    assert payload["evidence_count"] == 0
    assert "original_text" not in payload
    assert "evidence" not in payload
    assert "status_explanation" not in payload


def test_commitment_payload_exposes_ai_run_metadata_for_transparency():
    ai_run = SimpleNamespace(
        model_name="research-model",
        prompt_version="mvp-6",
        schema_version="mvp-6",
        methodology_version="2026-07-12.1",
        analysis_date=date(2026, 7, 12),
        task_type="commitment_status_analysis",
        status="imported",
    )
    status_update = SimpleNamespace(
        previous_status="not_started",
        new_status="fulfilled",
        new_status_group="completed",
        status_explanation="Done.",
        confidence="high",
        new_contribution_level="decisive",
        contribution_explanation="Cabinet action was decisive.",
        contribution_confidence="high",
        effective_date=date(2026, 7, 12),
        factual_review_status="not_reviewed",
        created_at=datetime(2026, 7, 12),
        ai_run=ai_run,
    )
    commitment = SimpleNamespace(
        id=uuid4(),
        display_code="1.1",
        title="Build hospitals",
        slug="build-hospitals",
        original_text="Original promise",
        normalized_description="Build hospitals.",
        topic=None,
        responsible_institutions=None,
        period=None,
        deadline=None,
        measurable_criteria=None,
        commitment_type=None,
        promised_item_type=None,
        baseline_mode=None,
        required_external_actors=None,
        control_level=None,
        evaluation_basis=None,
        contribution_types_text=None,
        official_program_change_note=None,
        source_version_note=None,
        quantitative_target=None,
        quantitative_actual=None,
        measure_validity_status=None,
        status="fulfilled",
        status_explanation="Done.",
        confidence_level="high",
        confidence_explanation="Strong evidence.",
        contribution_level="decisive",
        contribution_explanation="Cabinet action was decisive.",
        contribution_confidence="high",
        last_status_update=date(2026, 7, 12),
        importance_level="key",
        importance_weight=3,
        is_key_commitment=True,
        display_order=1,
        program=program(),
        evidence=[],
        status_updates=[status_update],
    )

    payload = commitment_payload(commitment, include_evidence=True)

    assert payload["analysis_metadata"]["model_name"] == "research-model"
    assert payload["analysis_metadata"]["prompt_version"] == "mvp-6"
    assert payload["analysis_metadata"]["methodology_version"] == "2026-07-12.1"
    assert payload["status_history"][0]["ai_run"]["schema_version"] == "mvp-6"
