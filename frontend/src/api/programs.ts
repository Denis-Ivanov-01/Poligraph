import { apiGet } from "./client";
import type { ActiveGovernmentProgramSummary, Commitment, CommitmentsResponse, Program } from "../types/program";

export type CommitmentFilters = {
  status?: string;
  topic?: string;
  program_id?: string;
  key_only?: boolean;
};

function queryString(filters: CommitmentFilters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value !== undefined && value !== "" && value !== false) {
      params.set(key, String(value));
    }
  });
  const value = params.toString();
  return value ? `?${value}` : "";
}

export function getPrograms() {
  return apiGet<Program[]>("/programs");
}

export function getActiveGovernmentProgramSummary() {
  return apiGet<ActiveGovernmentProgramSummary | null>("/programs/active-summary");
}

export function getCommitments(filters: CommitmentFilters = {}) {
  return apiGet<CommitmentsResponse>(`/programs/commitments${queryString(filters)}`);
}

export function getCommitment(slug: string) {
  return apiGet<Commitment>(`/programs/commitments/${slug}`);
}
