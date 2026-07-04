import { apiGet } from "./client";
import type { Statement, StatementListItem } from "../types/statement";

export function getStatements(filters?: { q?: string }) {
  const params = new URLSearchParams();
  if (filters?.q) params.set("q", filters.q);
  const suffix = params.toString() ? `?${params.toString()}` : "";
  return apiGet<StatementListItem[]>(`/statements${suffix}`);
}

export function getStatementById(id: string) {
  return apiGet<Statement>(`/statements/${id}`);
}
