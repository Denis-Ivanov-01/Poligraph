from datetime import datetime

from pydantic import BaseModel, Field


class AiScores(BaseModel):
    factual_accuracy: int = Field(ge=0, le=100)
    logical_consistency: int = Field(ge=0, le=100)
    communicational_integrity: int = Field(ge=0, le=100)
    principle_consistency: int = Field(ge=0, le=100)
    overall: int = Field(ge=0, le=100)


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


class AiAnalysisInput(BaseModel):
    model_name: str
    prompt_version: str
    schema_version: str
    scores: AiAnalysisInputScores
    explanations: AiAnalysisInputExplanations
    source_urls: list[AiSourceUrl] = Field(default_factory=list)
    ai_details: AiDetails | None = None
