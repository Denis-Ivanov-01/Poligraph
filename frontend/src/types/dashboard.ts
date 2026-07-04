import type { StatementListItem } from "./statement";

export type Dashboard = {
  published_statement_count: number;
  party_count: number;
  politician_count: number;
  average_overall_score?: number | null;
  latest_statements: StatementListItem[];
};
