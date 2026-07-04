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
        "factual_accuracy": round(sum(analysis.factual_accuracy_score for analysis in analyses) / len(analyses), 2),
        "logical_consistency": round(sum(analysis.logical_consistency_score for analysis in analyses) / len(analyses), 2),
        "communicational_integrity": round(
            sum(analysis.communicational_integrity_score for analysis in analyses) / len(analyses),
            2,
        ),
        "principle_consistency": round(sum(analysis.principle_consistency_score for analysis in analyses) / len(analyses), 2),
        "overall": round(sum(analysis.overall_score for analysis in analyses) / len(analyses), 2),
    }


def analysis_payload(analysis: AiAnalysis | None) -> dict | None:
    if not analysis or not analysis.is_published:
        return None
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
