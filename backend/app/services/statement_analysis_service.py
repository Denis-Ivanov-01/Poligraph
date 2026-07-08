from datetime import datetime, timezone

from app.models.ai_analysis import AiAnalysis
from app.models.statement import Statement
from app.schemas.ai_analysis import AiAnalysisInput


def calculated_overall_score(scores) -> int:
    return int(
        round(
            (
                scores.factual_accuracy
                + scores.logical_consistency
                + scores.communicational_integrity
                + scores.principle_consistency
            )
            / 4
        )
    )


def apply_statement_ai_analysis(
    statement: Statement,
    data: AiAnalysisInput,
    raw_json: str,
    prompt_text: str,
) -> AiAnalysis:
    analysis = statement.ai_analysis or AiAnalysis(statement_id=statement.id)
    analysis.model_name = data.model_name
    analysis.prompt_version = data.prompt_version
    analysis.schema_version = data.schema_version
    analysis.analysis_date = datetime.now(timezone.utc)
    analysis.factual_accuracy_score = data.scores.factual_accuracy
    analysis.logical_consistency_score = data.scores.logical_consistency
    analysis.communicational_integrity_score = data.scores.communicational_integrity
    analysis.principle_consistency_score = data.scores.principle_consistency
    analysis.overall_score = calculated_overall_score(data.scores)
    analysis.factual_accuracy_explanation = data.explanations.factual_accuracy
    analysis.logical_consistency_explanation = data.explanations.logical_consistency
    analysis.communicational_integrity_explanation = data.explanations.communicational_integrity
    analysis.principle_consistency_explanation = data.explanations.principle_consistency
    analysis.overall_explanation = (
        "Calculated automatically as the average of factual accuracy, logical consistency, "
        "communicational integrity, and principle consistency."
    )
    analysis.prompt_text = prompt_text
    analysis.raw_ai_response = raw_json
    analysis.source_urls = [item.model_dump() for item in data.source_urls]
    analysis.is_published = False
    statement.generated_prompt_text = analysis.prompt_text
    return analysis
