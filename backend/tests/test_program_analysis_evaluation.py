import copy
import json
from pathlib import Path

from app.services.program_analysis_evaluation import evaluate_batch_against_standalone


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_cases():
    return json.loads((FIXTURE_DIR / "program_analysis_eval_reference.json").read_text(encoding="utf-8"))["cases"]


def test_reference_suite_covers_required_archetypes_and_48_item_scale_fixture():
    cases = load_cases()
    archetypes = {item["archetype"] for item in cases}
    assert len(cases) == 13
    assert {
        "clear legislative completion",
        "legislation proposed but not in force",
        "operational platform launch",
        "multi-component promise",
        "public-outcome promise",
        "negative or maintenance commitment",
        "inherited implementation",
        "shared-control result",
        "absent evidence",
        "contradictory evidence",
        "dynamic quantitative data",
        "contribution attribution",
        "broad ambiguous language and SIGMA-style platform",
    } <= archetypes
    scale_fixture = json.loads((FIXTURE_DIR / "program_analysis_batch_48.json").read_text(encoding="utf-8"))
    assert len(scale_fixture["commitments"]) == 48
    assert len({item["commitment_ref"] for item in scale_fixture["commitments"]}) == 48


def test_evaluation_reports_perfect_metrics_for_matching_standalone_references():
    references = load_cases()
    result = evaluate_batch_against_standalone(references, copy.deepcopy(references))
    assert result["matched_case_count"] == 13
    assert result["missing_candidate_case_ids"] == []
    for metric in result["metrics"].values():
        assert metric == 1.0 or metric == 0.0
    assert result["metrics"]["exact_current_status_agreement"] == 1.0
    assert result["metrics"]["material_component_coverage"] == 1.0
    assert result["metrics"]["human_review_recall"] == 1.0
    assert result["metrics"]["unsupported_claim_rate"] == 0.0
    assert result["metrics"]["missing_source_ref_rate"] == 0.0


def test_evaluation_detects_known_batch_failure_patterns():
    references = load_cases()
    candidates = copy.deepcopy(references)
    sigma = next(item for item in candidates if item["case_id"] == "sigma-platform")
    sigma["current_status"] = "fulfilled"
    sigma["baseline_mode"] = "new_policy"
    sigma["control_level"] = "direct"
    sigma["contribution_level"] = "decisive"
    sigma["material_components"] = sigma["material_components"][:1]
    sigma["human_review_recommended"] = False
    sigma["sources"] = sigma["sources"][:1]
    sigma["evidence_links"][0]["source_ref"] = "MISSING"

    result = evaluate_batch_against_standalone(references, candidates)
    assert result["metrics"]["exact_current_status_agreement"] < 1.0
    assert result["metrics"]["baseline_mode_agreement"] < 1.0
    assert result["metrics"]["control_level_agreement"] < 1.0
    assert result["metrics"]["contribution_level_agreement"] < 1.0
    assert result["metrics"]["material_component_coverage"] < 1.0
    assert result["metrics"]["human_review_recall"] < 1.0
    assert result["metrics"]["missing_source_ref_rate"] > 0.0
