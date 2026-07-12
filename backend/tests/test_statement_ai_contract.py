import json
from types import SimpleNamespace

import pytest

from app.services.ai_prompt_service import build_statement_prompt
from app.services.ai_json_validation_service import validate_ai_json
from app.services.commitment_service import EVIDENCE_SOURCE_TYPES


def valid_statement_payload():
    return {
        "model_name": "model",
        "prompt_version": "mvp-3",
        "schema_version": "mvp-3",
        "statement_analysis": {
            "factual_accuracy_applicability": "applicable",
            "scores": {
                "factual_accuracy": 80,
                "logical_consistency": 75,
                "communicational_integrity": 70,
                "principle_consistency": 100,
            },
            "explanations": {
                "factual_accuracy": "Supported by official data.",
                "logical_consistency": "The conclusion follows the premise.",
                "communicational_integrity": "The framing is clear.",
                "principle_consistency": "No contradiction found.",
            },
            "evidence_review_completeness": "partial",
            "human_review_recommended": False,
            "human_review_reason": None,
        },
        "claims": [
            {
                "claim_ref": "C1",
                "exact_quote": "Quote",
                "normalized_claim": "Normalized claim",
                "claim_type": "factual",
                "checkability": "checkable",
                "materiality": "high",
                "materiality_reason": "Central factual claim.",
                "ai_verification_status": "supported",
                "confidence_level": "high",
                "evidence_summary": "Source supports it.",
                "missing_or_uncertain_evidence": None,
                "used_for_dimensions": ["factual_accuracy"],
                "source_refs": ["S1"],
            }
        ],
        "sources": [
            {
                "source_ref": "S1",
                "title": "Official document",
                "url": "https://example.test/source",
                "source_type": "government_document",
                "publisher": "Institution",
                "published_at": "2026-01-01",
                "quote_or_relevant_excerpt": "Excerpt",
                "description": "Description",
                "reliability_level": "high",
            }
        ],
    }


def test_statement_ai_contract_accepts_valid_enums():
    payload = valid_statement_payload()

    result = validate_ai_json(json.dumps(payload))

    assert result.statement_analysis["evidence_review_completeness"] == "partial"


def test_statement_ai_contract_rejects_invalid_statement_enum():
    payload = valid_statement_payload()
    payload["statement_analysis"]["evidence_review_completeness"] = "mostly"

    with pytest.raises(ValueError, match="evidence_review_completeness"):
        validate_ai_json(json.dumps(payload))


def test_statement_ai_contract_rejects_invalid_claim_and_source_enums():
    payload = valid_statement_payload()
    payload["claims"][0]["claim_type"] = "vibe"

    with pytest.raises(ValueError, match="claim_type"):
        validate_ai_json(json.dumps(payload))

    payload = valid_statement_payload()
    payload["sources"][0]["source_type"] = "blog"

    with pytest.raises(ValueError, match="source_type"):
        validate_ai_json(json.dumps(payload))


def test_statement_prompt_and_validator_use_runtime_evidence_source_types():
    EVIDENCE_SOURCE_TYPES["temporary_statement_source"] = "Temporary statement source"
    try:
        statement = SimpleNamespace(
            id="statement-1",
            title="Statement",
            source_type="speech",
            source_url="https://example.test/statement",
            statement_date=None,
            politician=None,
            politician_id=None,
            party_at_statement_time=None,
            original_text="Statement text",
        )
        prompt = build_statement_prompt(statement)
        assert "temporary_statement_source" in prompt

        payload = valid_statement_payload()
        payload["sources"][0]["source_type"] = "temporary_statement_source"
        result = validate_ai_json(json.dumps(payload))
        assert result.sources[0]["source_type"] == "temporary_statement_source"
    finally:
        EVIDENCE_SOURCE_TYPES.pop("temporary_statement_source", None)
