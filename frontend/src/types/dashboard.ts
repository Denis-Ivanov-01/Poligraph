import type { StatementListItem } from "./statement";
import type { ActiveGovernmentProgramSummary } from "./program";

export type DashboardRankingItem = {
  id: string;
  slug: string;
  full_name: string;
  short_name?: string | null;
  average_overall_score: number;
  analyzed_statement_count: number;
};

export type Dashboard = {
  published_statement_count: number;
  party_count: number;
  politician_count: number;
  average_overall_score?: number | null;
  latest_statements: StatementListItem[];
  top_politicians: DashboardRankingItem[];
  top_parties: DashboardRankingItem[];
  active_government_program_summary?: ActiveGovernmentProgramSummary | null;
};
