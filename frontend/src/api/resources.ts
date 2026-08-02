import { API_BASE_URL } from "../app/config";
import publicResourceFallback from "../../../resources/bg-BG/resources.json";
import { apiGet } from "./client";

export function getResources(locale = "bg-BG") {
  return apiGet<typeof publicResourceFallback>(`/resources/${locale}/resources`);
}

export async function getMethodology(page: string, locale = "bg-BG") {
  const response = await fetch(`${API_BASE_URL}/resources/${locale}/methodology/${page}`, {
    method: "GET",
    headers: { Accept: "text/markdown, text/plain" }
  });
  if (!response.ok) {
    throw new Error(`Methodology content request failed with status ${response.status}.`);
  }
  return response.text();
}
