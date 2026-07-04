import type { PoliticalParty } from "./politicalParty";
import type { CriteriaAverages } from "./aiAnalysis";
import type { StatementListItem } from "./statement";

export type Politician = {
  id: string;
  slug: string;
  full_name: string;
  biography?: string | null;
  image_url?: string | null;
  current_party?: PoliticalParty | null;
  average_scores?: CriteriaAverages | null;
  statements?: StatementListItem[];
};
