import { apiGet } from "./client";
import type { PoliticalParty } from "../types/politicalParty";
import type { Politician } from "../types/politician";
import type { StatementListItem } from "../types/statement";

export type SearchResults = {
  parties: PoliticalParty[];
  politicians: Politician[];
  statements: StatementListItem[];
};

export function search(query: string) {
  return apiGet<SearchResults>(`/search?q=${encodeURIComponent(query)}`);
}
