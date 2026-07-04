export type AiScores = {
  factual_accuracy: number;
  logical_consistency: number;
  communicational_integrity: number;
  principle_consistency: number;
  overall: number;
};

export type CriteriaAverages = AiScores;

export type AiExplanations = {
  factual_accuracy: string;
  logical_consistency: string;
  communicational_integrity: string;
  principle_consistency: string;
  overall: string;
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
  ai_details: {
    prompt_text: string;
    raw_ai_response: string;
  };
};
