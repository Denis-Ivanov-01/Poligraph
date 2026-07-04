from app.models.ai_analysis import AiAnalysis


def scores_dict(analysis: AiAnalysis) -> dict[str, int]:
    return {
        "factual_accuracy": analysis.factual_accuracy_score,
        "logical_consistency": analysis.logical_consistency_score,
        "communicational_integrity": analysis.communicational_integrity_score,
        "principle_consistency": analysis.principle_consistency_score,
        "overall": analysis.overall_score,
    }


def explanations_dict(analysis: AiAnalysis) -> dict[str, str]:
    return {
        "factual_accuracy": analysis.factual_accuracy_explanation,
        "logical_consistency": analysis.logical_consistency_explanation,
        "communicational_integrity": analysis.communicational_integrity_explanation,
        "principle_consistency": analysis.principle_consistency_explanation,
        "overall": analysis.overall_explanation,
    }
