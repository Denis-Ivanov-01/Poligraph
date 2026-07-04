import { apiGet } from "./client";
import type { Politician } from "../types/politician";

export function getPoliticians() {
  return apiGet<Politician[]>("/politicians");
}

export function getPoliticianBySlug(slug: string) {
  return apiGet<Politician>(`/politicians/${slug}`);
}
