import { apiGet } from "./client";
import type {
  ActiveGovernmentProgramSummary,
  Commitment,
  CommitmentsResponse,
  Program,
  ProgramCommitmentsPage,
  ProgramDetails,
  ProgramSectionResponse
} from "../types/program";

export type CommitmentFilters = {
  status?: string;
  topic?: string;
  program_id?: string;
  key_only?: boolean;
};

export type ProgramCommitmentQuery = {
  q?: string;
  status?: string;
  confidence?: string;
  sort?: string;
  limit?: number;
  offset?: number;
};

function queryString(filters: CommitmentFilters | ProgramCommitmentQuery) {
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

export function getProgram(id: string) {
  return apiGet<ProgramDetails>(`/programs/${id}`);
}

export function getProgramSectionSubsections(programId: string, sectionId: string) {
  return apiGet<ProgramSectionResponse>(`/programs/${programId}/sections/${sectionId}/subsections`);
}

export function getProgramSectionCommitments(programId: string, sectionId: string, query: ProgramCommitmentQuery = {}) {
  return apiGet<ProgramCommitmentsPage>(`/programs/${programId}/sections/${sectionId}/commitments${queryString(query)}`);
}

export function searchProgramCommitments(programId: string, query: ProgramCommitmentQuery = {}, signal?: AbortSignal) {
  return apiGet<ProgramCommitmentsPage>(`/programs/${programId}/commitments${queryString(query)}`, { signal });
}

export function getActiveGovernmentProgramSummary() {
  return apiGet<ActiveGovernmentProgramSummary | null>("/programs/active-summary");
}

export function getCommitments(filters: CommitmentFilters = {}) {
  return apiGet<CommitmentsResponse>(`/programs/commitments${queryString(filters)}`);
}

export function getCommitmentBySlug(slug: string) {
  return apiGet<Commitment>(`/programs/commitments/${slug}`);
}

export function getCommitment(programId: string, slug: string) {
  return apiGet<Commitment>(`/programs/${programId}/commitments/${slug}`);
}
