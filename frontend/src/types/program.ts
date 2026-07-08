import type { PoliticalParty } from "./politicalParty";

export type Program = {
  id: string;
  title: string;
  slug: string;
  description?: string | null;
  program_type: string;
  program_type_label: string;
  political_subject_name: string;
  related_party?: PoliticalParty | null;
  related_coalition_name?: string | null;
  period_start?: string | null;
  period_end?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  source_description?: string | null;
  is_active_government_program: boolean;
};

export type CommitmentEvidence = {
  id: string;
  title: string;
  url?: string | null;
  source_type: string;
  source_type_label: string;
  publisher?: string | null;
  published_at?: string | null;
  quote_or_relevant_excerpt?: string | null;
  description?: string | null;
  supports_status: boolean;
};

export type Commitment = {
  id: string;
  title: string;
  slug: string;
  original_text?: string | null;
  normalized_description?: string | null;
  topic?: string | null;
  responsible_institutions?: string | null;
  period?: string | null;
  deadline?: string | null;
  measurable_criteria?: string | null;
  status: string;
  status_label: string;
  status_group: string;
  status_group_label: string;
  status_explanation?: string | null;
  confidence_level: string;
  confidence_label: string;
  confidence_explanation?: string | null;
  last_status_update?: string | null;
  is_key_commitment: boolean;
  display_order: number;
  program: Program;
  evidence_count: number;
  evidence?: CommitmentEvidence[];
};

export type CommitmentsResponse = {
  items: Commitment[];
  topics: string[];
};

export type ActiveGovernmentProgramSummary = {
  program: Program;
  total_commitments: number;
  status_counts: Record<string, number>;
  key_commitments: Commitment[];
};
