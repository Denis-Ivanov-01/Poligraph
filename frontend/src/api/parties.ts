import { apiGet } from "./client";
import type { PoliticalParty } from "../types/politicalParty";

export function getParties() {
  return apiGet<PoliticalParty[]>("/parties");
}

export function getPartyBySlug(slug: string) {
  return apiGet<PoliticalParty>(`/parties/${slug}`);
}
