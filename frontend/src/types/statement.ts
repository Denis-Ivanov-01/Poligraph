import type { AiAnalysis } from "./aiAnalysis";
import type { PoliticalParty } from "./politicalParty";

export type StatementPolitician = {
  id: string;
  slug: string;
  full_name: string;
};

export type MediaAsset = {
  id: string;
  file_path: string;
  media_type: string;
  original_filename?: string | null;
};

export type StatementListItem = {
  id: string;
  title?: string | null;
  source_type: string;
  statement_date?: string | null;
  politician: StatementPolitician;
  party_at_statement_time?: PoliticalParty | null;
  overall_score?: number | null;
};

export type Statement = StatementListItem & {
  source_url?: string | null;
  original_text: string;
  media: MediaAsset[];
  ai_analysis?: AiAnalysis | null;
};
