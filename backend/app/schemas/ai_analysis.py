from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.commitment_service import EVIDENCE_SOURCE_TYPES


STATEMENT_FACTUAL_ACCURACY_APPLICABILITIES = {"applicable", "not_applicable"}
STATEMENT_EVIDENCE_REVIEW_COMPLETENESS_VALUES = {"complete", "partial", "limited_by_public_evidence"}
STATEMENT_CLAIM_TYPES = {
    "factual",
    "institutional",
    "opinion",
    "prediction",
    "promise",
    "value_judgment",
    "rhetorical",
    "mixed",
}
STATEMENT_CHECKABILITY_VALUES = {"checkable", "partially_checkable", "not_checkable"}
STATEMENT_MATERIALITY_VALUES = {"low", "medium", "high"}
STATEMENT_VERIFICATION_STATUSES = {
    "supported",
    "approximately_supported",
    "misleading",
    "contradicted",
    "genuinely_unresolved",
    "not_fact_checked",
    "not_applicable",
}
STATEMENT_CONFIDENCE_LEVELS = {"low", "medium", "high"}
STATEMENT_DIMENSIONS = {
    "factual_accuracy",
    "logical_consistency",
    "communicational_integrity",
    "principle_consistency",
}
AI_EVIDENCE_SOURCE_TYPES = EVIDENCE_SOURCE_TYPES


def _reject_unknown_keys(value: dict, allowed: set[str], field_name: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{field_name} contains unknown keys: {', '.join(sorted(unknown))}.")


def _validate_enum(value, allowed: set[str], field_name: str, *, required: bool = False) -> None:
    if value in (None, ""):
        if required:
            raise ValueError(f"{field_name} is required.")
        return
    if value not in allowed:
        raise ValueError(f"{field_name} is invalid.")


class AiScores(BaseModel):
    factual_accuracy: int | None = Field(default=None, ge=0, le=100)
    logical_consistency: int | None = Field(default=None, ge=0, le=100)
    communicational_integrity: int | None = Field(default=None, ge=0, le=100)
    principle_consistency: int | None = Field(default=None, ge=0, le=100)
    overall: int | None = Field(default=None, ge=0, le=100)


class AiExplanations(BaseModel):
    factual_accuracy: str
    logical_consistency: str
    communicational_integrity: str
    principle_consistency: str
    overall: str


class AiAnalysisInputScores(BaseModel):
    factual_accuracy: int = Field(ge=0, le=100)
    logical_consistency: int = Field(ge=0, le=100)
    communicational_integrity: int = Field(ge=0, le=100)
    principle_consistency: int = Field(ge=0, le=100)


class AiAnalysisInputExplanations(BaseModel):
    factual_accuracy: str
    logical_consistency: str
    communicational_integrity: str
    principle_consistency: str


class AiSourceUrl(BaseModel):
    url: str
    description: str | None = None


class AiDetails(BaseModel):
    prompt_text: str
    raw_ai_response: str


class AiAnalysisPublic(BaseModel):
    model_name: str
    prompt_version: str
    schema_version: str
    analysis_date: datetime
    scores: AiScores
    explanations: AiExplanations
    source_urls: list[AiSourceUrl] = Field(default_factory=list)
    ai_details: AiDetails
    evidence_review_completeness: str | None = None
    human_review_recommended: bool | None = None
    human_review_reason: str | None = None
    structural_review_status: str | None = None
    factual_review_status: str | None = None
    claims: list[dict] = Field(default_factory=list)
    disclaimer: str | None = None


class AiAnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model_name: str
    prompt_version: str
    schema_version: str
    statement_analysis: dict
    claims: list[dict] = Field(default_factory=list)
    sources: list[dict] = Field(default_factory=list)
    ai_details: AiDetails | None = None

    @field_validator("statement_analysis")
    @classmethod
    def validate_statement_analysis_contract(cls, value: dict) -> dict:
        if not isinstance(value, dict):
            raise ValueError("statement_analysis must be an object.")
        _reject_unknown_keys(
            value,
            {
                "factual_accuracy_applicability",
                "scores",
                "explanations",
                "evidence_review_completeness",
                "human_review_recommended",
                "human_review_reason",
            },
            "statement_analysis",
        )
        _validate_enum(
            value.get("factual_accuracy_applicability"),
            STATEMENT_FACTUAL_ACCURACY_APPLICABILITIES,
            "statement_analysis.factual_accuracy_applicability",
        )
        _validate_enum(
            value.get("evidence_review_completeness"),
            STATEMENT_EVIDENCE_REVIEW_COMPLETENESS_VALUES,
            "statement_analysis.evidence_review_completeness",
        )
        if "human_review_recommended" in value and not isinstance(value["human_review_recommended"], bool):
            raise ValueError("statement_analysis.human_review_recommended must be boolean.")
        if value.get("human_review_reason") is not None and not isinstance(value.get("human_review_reason"), str):
            raise ValueError("statement_analysis.human_review_reason must be a string or null.")

        scores = value.get("scores")
        if not isinstance(scores, dict):
            raise ValueError("statement_analysis.scores is required.")
        _reject_unknown_keys(scores, STATEMENT_DIMENSIONS, "statement_analysis.scores")
        AiAnalysisInputScores.model_validate(scores)

        explanations = value.get("explanations")
        if not isinstance(explanations, dict):
            raise ValueError("statement_analysis.explanations is required.")
        _reject_unknown_keys(explanations, STATEMENT_DIMENSIONS, "statement_analysis.explanations")
        AiAnalysisInputExplanations.model_validate(explanations)
        return value

    @field_validator("claims")
    @classmethod
    def validate_claim_contract(cls, value: list[dict]) -> list[dict]:
        if not isinstance(value, list):
            raise ValueError("claims must be a list.")
        allowed = {
            "claim_ref",
            "exact_quote",
            "normalized_claim",
            "claim_type",
            "checkability",
            "materiality",
            "materiality_reason",
            "ai_verification_status",
            "confidence_level",
            "evidence_summary",
            "missing_or_uncertain_evidence",
            "used_for_dimensions",
            "source_refs",
        }
        for index, claim in enumerate(value, start=1):
            if not isinstance(claim, dict):
                raise ValueError(f"claims[{index}] must be an object.")
            _reject_unknown_keys(claim, allowed, f"claims[{index}]")
            _validate_enum(claim.get("claim_type"), STATEMENT_CLAIM_TYPES, f"claims[{index}].claim_type")
            _validate_enum(claim.get("checkability"), STATEMENT_CHECKABILITY_VALUES, f"claims[{index}].checkability")
            _validate_enum(claim.get("materiality"), STATEMENT_MATERIALITY_VALUES, f"claims[{index}].materiality")
            _validate_enum(
                claim.get("ai_verification_status"),
                STATEMENT_VERIFICATION_STATUSES,
                f"claims[{index}].ai_verification_status",
            )
            _validate_enum(claim.get("confidence_level"), STATEMENT_CONFIDENCE_LEVELS, f"claims[{index}].confidence_level")
            dimensions = claim.get("used_for_dimensions") or []
            if not isinstance(dimensions, list) or any(item not in STATEMENT_DIMENSIONS for item in dimensions):
                raise ValueError(f"claims[{index}].used_for_dimensions must contain valid dimension keys.")
            source_refs = claim.get("source_refs") or []
            if not isinstance(source_refs, list) or any(not isinstance(item, str) for item in source_refs):
                raise ValueError(f"claims[{index}].source_refs must be a list of strings.")
        return value

    @field_validator("sources")
    @classmethod
    def validate_source_contract(cls, value: list[dict]) -> list[dict]:
        if not isinstance(value, list):
            raise ValueError("sources must be a list.")
        allowed = {
            "source_ref",
            "title",
            "url",
            "source_type",
            "publisher",
            "published_at",
            "quote_or_relevant_excerpt",
            "description",
            "reliability_level",
        }
        for index, source in enumerate(value, start=1):
            if not isinstance(source, dict):
                raise ValueError(f"sources[{index}] must be an object.")
            _reject_unknown_keys(source, allowed, f"sources[{index}]")
            _validate_enum(source.get("source_type"), set(EVIDENCE_SOURCE_TYPES), f"sources[{index}].source_type")
            _validate_enum(source.get("reliability_level"), STATEMENT_CONFIDENCE_LEVELS, f"sources[{index}].reliability_level")
        return value

    @property
    def scores(self) -> AiAnalysisInputScores:
        return AiAnalysisInputScores.model_validate(self.statement_analysis.get("scores", {}))

    @property
    def explanations(self) -> AiAnalysisInputExplanations:
        return AiAnalysisInputExplanations.model_validate(self.statement_analysis.get("explanations", {}))
