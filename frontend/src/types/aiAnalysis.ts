export type AiScores = {
  factual_accuracy: number | null;
  logical_consistency: number | null;
  communicational_integrity: number | null;
  principle_consistency: number | null;
  overall?: number | null;
};

export type CriteriaAverages = AiScores;

export type AiExplanations = {
  factual_accuracy: string;
  logical_consistency: string;
  communicational_integrity: string;
  principle_consistency: string;
  overall?: string;
};

export type AiSourceUrl = {
  url: string;
  description?: string | null;
};

export type AiAnalysis = {
  model_name: string;
  prompt_version: string;
  schema_version: string;
  analysis_date: string;
  scores: AiScores;
  explanations: AiExplanations;
  source_urls: AiSourceUrl[];
  sources?: Array<AiSourceUrl & {
    id: string;
    title: string;
    source_type: string;
    publisher?: string | null;
    reliability_level?: string | null;
    factual_review_status?: string | null;
  }>;
  claims?: Array<{
    id: string;
    display_code?: string | null;
    exact_quote: string;
    normalized_claim: string;
    claim_type: string;
    checkability: string;
    materiality: string;
    materiality_reason?: string | null;
    ai_verification_status: string;
    confidence_level: string;
    evidence_summary?: string | null;
    missing_or_uncertain_evidence?: string | null;
    factual_review_status: string;
    sources: AiSourceUrl[];
  }>;
  evidence_review_completeness?: string | null;
  human_review_recommended?: boolean | null;
  human_review_reason?: string | null;
  structural_review_status?: string | null;
  factual_review_status?: string | null;
  disclaimer?: string | null;
  ai_details: {
    prompt_text: string;
    raw_ai_response: string;
  };
};
