import type { CriteriaAverages } from "./aiAnalysis";
import type { Politician } from "./politician";
import type { StatementListItem } from "./statement";

export type PartyMember = {
  id: string;
  start_date?: string | null;
  end_date?: string | null;
  politician: Politician;
};

export type PoliticalParty = {
  id: string;
  slug: string;
  full_name: string;
  short_name: string;
  description?: string | null;
  average_scores?: CriteriaAverages | null;
  members?: PartyMember[];
  statements?: StatementListItem[];
};
