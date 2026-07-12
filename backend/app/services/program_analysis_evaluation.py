import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any


CATEGORICAL_FIELDS = ("current_status", "baseline_mode", "control_level", "contribution_level", "confidence")
REQUIRED_ANALYTICAL_FIELDS = (
    "current_status",
    "baseline_mode",
    "control_level",
    "contribution_level",
    "confidence",
    "status_explanation",
    "material_components",
    "evidence_links",
    "sources",
)


def _ratio(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 4) if denominator else None


def _parse_date(value: Any) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _latest_source_date(case: dict[str, Any]) -> date | None:
    values = []
    for source in case.get("sources") or []:
        for field in ("published_at", "accessed_at"):
            parsed = _parse_date(source.get(field)) if isinstance(source, dict) else None
            if parsed:
                values.append(parsed)
    return max(values) if values else None


def _component_refs(case: dict[str, Any]) -> set[str]:
    return {
        item.get("component_ref")
        for item in case.get("material_components") or []
        if isinstance(item, dict) and isinstance(item.get("component_ref"), str)
    }


def _source_refs(case: dict[str, Any]) -> set[str]:
    return {
        item.get("source_ref")
        for item in case.get("sources") or []
        if isinstance(item, dict) and isinstance(item.get("source_ref"), str)
    }


def _dangling_source_refs(case: dict[str, Any]) -> tuple[int, int]:
    sources = _source_refs(case)
    dangling = 0
    total = 0
    for link in case.get("evidence_links") or []:
        if not isinstance(link, dict):
            continue
        total += 1
        if link.get("source_ref") not in sources:
            dangling += 1
    for component in case.get("material_components") or []:
        if not isinstance(component, dict):
            continue
        for source_ref in component.get("evidence_refs") or []:
            total += 1
            if source_ref not in sources:
                dangling += 1
    return dangling, total


def _unsupported_claims(case: dict[str, Any]) -> tuple[int, int]:
    source_refs = _source_refs(case)
    component_refs = _component_refs(case)
    unsupported = 0
    total = 0
    for link in case.get("evidence_links") or []:
        if not isinstance(link, dict):
            continue
        total += 1
        linked_components = set(link.get("component_refs") or [])
        if (
            link.get("source_ref") not in source_refs
            or not link.get("claim")
            or not linked_components
            or bool(linked_components - component_refs)
        ):
            unsupported += 1
    return unsupported, total


def evaluate_batch_against_standalone(
    references: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    reference_by_id = {item["case_id"]: item for item in references}
    candidate_by_id = {item["case_id"]: item for item in candidates}
    matched_ids = sorted(set(reference_by_id) & set(candidate_by_id))
    categorical_matches = {field: 0 for field in CATEGORICAL_FIELDS}
    component_expected = component_matched = 0
    source_types_expected = source_types_matched = 0
    contradiction_expected = contradiction_matched = 0
    freshness_expected = freshness_matched = 0
    quantitative_expected = quantitative_matched = 0
    review_expected = review_matched = 0
    dangling = dangling_total = 0
    unsupported = unsupported_total = 0
    complete_outputs = 0

    case_results = []
    for case_id in matched_ids:
        reference = reference_by_id[case_id]
        candidate = candidate_by_id[case_id]
        agreements = {}
        for field in CATEGORICAL_FIELDS:
            agreements[field] = candidate.get(field) == reference.get(field)
            categorical_matches[field] += int(agreements[field])

        reference_components = _component_refs(reference)
        candidate_components = _component_refs(candidate)
        component_expected += len(reference_components)
        component_matched += len(reference_components & candidate_components)

        reference_source_types = {
            item.get("source_type") for item in reference.get("sources") or [] if isinstance(item, dict) and item.get("source_type")
        }
        candidate_source_types = {
            item.get("source_type") for item in candidate.get("sources") or [] if isinstance(item, dict) and item.get("source_type")
        }
        source_types_expected += len(reference_source_types)
        source_types_matched += len(reference_source_types & candidate_source_types)

        expects_contradiction = any(
            isinstance(link, dict) and (link.get("is_contradictory") or link.get("evidence_strength") == "contradictory")
            for link in reference.get("evidence_links") or []
        )
        if expects_contradiction:
            contradiction_expected += 1
            contradiction_matched += int(
                any(
                    isinstance(link, dict) and (link.get("is_contradictory") or link.get("evidence_strength") == "contradictory")
                    for link in candidate.get("evidence_links") or []
                )
            )

        reference_freshness = _latest_source_date(reference)
        candidate_freshness = _latest_source_date(candidate)
        if reference_freshness:
            freshness_expected += 1
            freshness_matched += int(bool(candidate_freshness and candidate_freshness >= reference_freshness))

        reference_quantitative_date = _parse_date(reference.get("quantitative_actual_as_of"))
        candidate_quantitative_date = _parse_date(candidate.get("quantitative_actual_as_of"))
        if reference_quantitative_date:
            quantitative_expected += 1
            quantitative_matched += int(bool(candidate_quantitative_date and candidate_quantitative_date >= reference_quantitative_date))

        if reference.get("human_review_recommended"):
            review_expected += 1
            review_matched += int(bool(candidate.get("human_review_recommended")))

        case_dangling, case_dangling_total = _dangling_source_refs(candidate)
        dangling += case_dangling
        dangling_total += case_dangling_total
        case_unsupported, case_unsupported_total = _unsupported_claims(candidate)
        unsupported += case_unsupported
        unsupported_total += case_unsupported_total
        is_complete = all(candidate.get(field) is not None and candidate.get(field) != "" for field in REQUIRED_ANALYTICAL_FIELDS)
        complete_outputs += int(is_complete)
        case_results.append(
            {
                "case_id": case_id,
                "categorical_agreement": agreements,
                "output_complete": is_complete,
                "dangling_source_refs": case_dangling,
                "unsupported_claim_links": case_unsupported,
            }
        )

    count = len(matched_ids)
    return {
        "reference_case_count": len(references),
        "candidate_case_count": len(candidates),
        "matched_case_count": count,
        "missing_candidate_case_ids": sorted(set(reference_by_id) - set(candidate_by_id)),
        "unknown_candidate_case_ids": sorted(set(candidate_by_id) - set(reference_by_id)),
        "metrics": {
            "exact_current_status_agreement": _ratio(categorical_matches["current_status"], count),
            "baseline_mode_agreement": _ratio(categorical_matches["baseline_mode"], count),
            "control_level_agreement": _ratio(categorical_matches["control_level"], count),
            "contribution_level_agreement": _ratio(categorical_matches["contribution_level"], count),
            "confidence_calibration_agreement": _ratio(categorical_matches["confidence"], count),
            "material_component_coverage": _ratio(component_matched, component_expected),
            "evidence_source_type_coverage": _ratio(source_types_matched, source_types_expected),
            "contradictory_evidence_coverage": _ratio(contradiction_matched, contradiction_expected),
            "source_freshness": _ratio(freshness_matched, freshness_expected),
            "quantitative_data_freshness": _ratio(quantitative_matched, quantitative_expected),
            "unsupported_claim_rate": _ratio(unsupported, unsupported_total),
            "missing_source_ref_rate": _ratio(dangling, dangling_total),
            "human_review_recall": _ratio(review_matched, review_expected),
            "output_completeness": _ratio(complete_outputs, count),
        },
        "case_results": case_results,
    }


def _load_cases(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("cases")
    if not isinstance(payload, list):
        raise ValueError(f"{path} must contain a JSON list or an object with a cases list.")
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare batch commitment analyses with standalone reference analyses.")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--candidate", required=True)
    args = parser.parse_args(argv)
    result = evaluate_batch_against_standalone(_load_cases(args.reference), _load_cases(args.candidate))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["missing_candidate_case_ids"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
