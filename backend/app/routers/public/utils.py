from app.models.ai_analysis import AiAnalysis
from app.models.statement import Statement


SCORE_KEYS = (
    "factual_accuracy",
    "logical_consistency",
    "communicational_integrity",
    "principle_consistency",
)


def average_scores_payload(statements: list[Statement]) -> dict[str, float] | None:
    analyses = [
        statement.ai_analysis
        for statement in statements
        if statement.ai_analysis and statement.ai_analysis.is_published
    ]
    if not analyses:
        return None
    return {
        "factual_accuracy": round(sum((analysis.factual_accuracy_score or 0) for analysis in analyses) / len(analyses), 2),
        "logical_consistency": round(sum((analysis.logical_consistency_score or 0) for analysis in analyses) / len(analyses), 2),
        "communicational_integrity": round(
            sum((analysis.communicational_integrity_score or 0) for analysis in analyses) / len(analyses),
            2,
        ),
        "principle_consistency": round(sum((analysis.principle_consistency_score or 0) for analysis in analyses) / len(analyses), 2),
        "overall": round(sum((analysis.overall_score or 0) for analysis in analyses) / len(analyses), 2),
    }


def analysis_payload(analysis: AiAnalysis | None) -> dict | None:
    if not analysis or not analysis.is_published:
        return None
    claims = []
    sources = {}
    for claim in analysis.claims:
        claim_sources = []
        for link in claim.evidence_links:
            evidence = link.evidence_item
            if not evidence:
                continue
            source_payload = {
                "id": evidence.id,
                "title": evidence.title,
                "url": evidence.url,
                "source_type": evidence.source_type,
                "publisher": evidence.publisher,
                "published_at": evidence.published_at,
                "quote_or_relevant_excerpt": evidence.quote_or_relevant_excerpt,
                "description": evidence.description,
                "reliability_level": evidence.reliability_level,
                "factual_review_status": evidence.factual_review_status,
            }
            sources[str(evidence.id)] = source_payload
            claim_sources.append({**source_payload, "relation_type": link.relation_type, "note": link.note})
        claims.append(
            {
                "id": claim.id,
                "display_code": claim.display_code,
                "exact_quote": claim.exact_quote,
                "normalized_claim": claim.normalized_claim,
                "claim_type": claim.claim_type,
                "checkability": claim.checkability,
                "materiality": claim.materiality,
                "materiality_reason": claim.materiality_reason,
                "ai_verification_status": claim.ai_verification_status,
                "confidence_level": claim.confidence_level,
                "evidence_summary": claim.evidence_summary,
                "missing_or_uncertain_evidence": claim.missing_or_uncertain_evidence,
                "factual_review_status": claim.factual_review_status,
                "sources": claim_sources,
            }
        )
    return {
        "model_name": analysis.model_name,
        "prompt_version": analysis.prompt_version,
        "schema_version": analysis.schema_version,
        "analysis_date": analysis.analysis_date,
        "scores": {
            "factual_accuracy": analysis.factual_accuracy_score,
            "logical_consistency": analysis.logical_consistency_score,
            "communicational_integrity": analysis.communicational_integrity_score,
            "principle_consistency": analysis.principle_consistency_score,
            "overall": analysis.overall_score,
        },
        "explanations": {
            "factual_accuracy": analysis.factual_accuracy_explanation,
            "logical_consistency": analysis.logical_consistency_explanation,
            "communicational_integrity": analysis.communicational_integrity_explanation,
            "principle_consistency": analysis.principle_consistency_explanation,
            "overall": analysis.overall_explanation,
        },
        "source_urls": analysis.source_urls or [],
        "sources": list(sources.values()),
        "claims": claims,
        "evidence_review_completeness": analysis.evidence_review_completeness,
        "human_review_recommended": analysis.human_review_recommended,
        "human_review_reason": analysis.human_review_reason,
        "structural_review_status": analysis.structural_review_status,
        "factual_review_status": analysis.factual_review_status,
        "disclaimer": (
            "This analysis was generated with AI according to the platform methodology and passed structural "
            "moderation review. This does not mean every source was manually fact-checked by a moderator. "
            "If an error is found, the analysis may be corrected."
        ),
        "ai_details": {
            "prompt_text": analysis.prompt_text,
            "raw_ai_response": analysis.raw_ai_response,
        },
    }


def statement_list_payload(statement: Statement) -> dict:
    return {
        "id": statement.id,
        "title": statement.title,
        "source_type": statement.source_type,
        "statement_date": statement.statement_date,
        "politician": statement.politician,
        "party_at_statement_time": statement.party_at_statement_time,
        "overall_score": statement.ai_analysis.overall_score if statement.ai_analysis and statement.ai_analysis.is_published else None,
    }


def statement_detail_payload(statement: Statement) -> dict:
    payload = statement_list_payload(statement)
    payload.update(
        {
            "source_url": statement.source_url,
            "original_text": statement.original_text,
            "media": statement.media,
            "ai_analysis": analysis_payload(statement.ai_analysis),
        }
    )
    return payload
