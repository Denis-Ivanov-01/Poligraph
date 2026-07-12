import type { PoliticalParty } from "./politicalParty";

export type Program = {
  id: string;
  display_code?: string | null;
  title: string;
  slug: string;
  description?: string | null;
  short_description?: string | null;
  program_type: string;
  program_type_label: string;
  political_subject_name: string;
  related_party?: PoliticalParty | null;
  related_coalition_name?: string | null;
  period_text?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  publication_date?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  source_description?: string | null;
  source_acquisition_method?: string | null;
  source_coverage_status?: "full" | "partial" | "unknown" | null;
  source_acquisition_note?: string | null;
  source_document_complete?: boolean | null;
  supplementary_source_urls?: string[];
  is_active_government_program: boolean;
  structural_review_status?: string | null;
  factual_review_status?: string | null;
  status_counts?: Record<string, number>;
  total_commitments?: number;
  score_summary?: ProgramScoreSummary | null;
};

export type ProgramScoreSummary = {
  fulfillment_score?: number | null;
  overall_score?: number | null;
  coverage?: number | null;
  contribution_coverage?: number | null;
  total_commitments: number;
  due_commitments: number;
  analyzed_commitments: number;
  total_weight: number;
  due_weight: number;
  analyzed_weight: number;
  unclear_count: number;
  not_analyzed_count: number;
  indeterminate_contribution_count: number;
  violated_count: number;
  abandoned_count: number;
  contribution_counts: Record<string, number>;
};

export type CommitmentEvidence = {
  id: string;
  title: string;
  url?: string | null;
  source_type: string;
  source_type_label: string;
  publisher?: string | null;
  published_at?: string | null;
  accessed_at?: string | null;
  quote_or_relevant_excerpt?: string | null;
  description?: string | null;
  supports_status: boolean;
  relation_type: string;
  evidence_role?: string | null;
  evidence_role_label?: string | null;
  evidence_strength?: string | null;
  evidence_strength_label?: string | null;
  is_self_reported: boolean;
  is_independent_confirmation: boolean;
  is_contradictory: boolean;
  is_disproven: boolean;
  limitations?: string | null;
  claim?: string | null;
  factual_review_status: string;
};

export type AiRunMetadata = {
  model_name?: string | null;
  prompt_version?: string | null;
  schema_version?: string | null;
  methodology_version?: string | null;
  analysis_date?: string | null;
  task_type?: string | null;
  status?: string | null;
};

export type CommitmentStatusUpdate = {
  previous_status?: string | null;
  new_status: string;
  new_status_group: string;
  status_explanation?: string | null;
  confidence: string;
  contribution_level?: string | null;
  contribution_label?: string | null;
  contribution_explanation?: string | null;
  contribution_confidence?: string | null;
  effective_date?: string | null;
  factual_review_status: string;
  created_at: string;
  ai_run?: AiRunMetadata | null;
};

export type Commitment = {
  id: string;
  display_code?: string | null;
  title: string;
  slug: string;
  original_text?: string | null;
  normalized_description?: string | null;
  topic?: string | null;
  responsible_institutions?: string | null;
  period?: string | null;
  deadline?: string | null;
  measurable_criteria?: string | null;
  commitment_type?: string | null;
  commitment_type_label?: string | null;
  promised_item_type?: string | null;
  baseline_mode?: string | null;
  baseline_mode_label?: string | null;
  required_external_actors?: string | null;
  control_level?: string | null;
  control_level_label?: string | null;
  evaluation_basis?: string | null;
  contribution_types?: string | null;
  official_program_change_note?: string | null;
  source_version_note?: string | null;
  quantitative_target?: string | null;
  quantitative_actual?: string | null;
  measure_validity_status?: string | null;
  measure_validity_label?: string | null;
  status: string;
  status_label: string;
  status_group: string;
  status_group_label: string;
  status_explanation?: string | null;
  confidence_level?: string | null;
  confidence_label?: string | null;
  confidence_explanation?: string | null;
  contribution_level?: string | null;
  contribution_label?: string | null;
  contribution_explanation?: string | null;
  contribution_confidence?: string | null;
  contribution_confidence_label?: string | null;
  last_status_update?: string | null;
  importance_level?: string | null;
  importance_label?: string | null;
  importance_weight?: number | null;
  is_key_commitment: boolean;
  display_order: number;
  program_section_id?: string | null;
  program: Program;
  evidence_count: number;
  analysis_metadata?: AiRunMetadata | null;
  evidence?: CommitmentEvidence[];
  status_history?: CommitmentStatusUpdate[];
};

export type CommitmentsResponse = {
  items: Commitment[];
  topics: string[];
};

export type ActiveGovernmentProgramSummary = {
  program: Program;
  total_commitments: number;
  status_counts: Record<string, number>;
  score_summary?: ProgramScoreSummary | null;
  key_commitments: Commitment[];
};

export type ProgramSection = {
  id: string;
  section_code?: string | null;
  title: string;
  summary?: string | null;
  policy_area?: string | null;
  display_order: number;
  status_counts: Record<string, number>;
  commitment_count: number;
  direct_commitment_count: number;
  child_section_count: number;
  has_subsections: boolean;
  has_commitments: boolean;
};

export type ProgramDetails = Program & {
  sections: ProgramSection[];
  disclaimer?: string | null;
  last_commitment_update?: string | null;
};

export type ProgramSectionResponse = {
  items: ProgramSection[];
};

export type ProgramCommitmentsPage = {
  items: Commitment[];
  total_count: number;
  limit: number;
  offset: number;
  next_offset?: number | null;
  has_more: boolean;
};
