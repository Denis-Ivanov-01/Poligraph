import { API_BASE_URL } from "../app/config";
import { formatResource, text } from "../i18n/resources";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number
  ) {
    super(message);
  }
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    headers: { Accept: "application/json" }
  });
  if (!response.ok) {
    let message = formatResource(text.api.requestFailed, { status: response.status });
    try {
      const body = await response.json();
      message = body.detail ?? message;
    } catch {
      // Keep the generic message when the response is not JSON.
    }
    throw new ApiError(message, response.status);
  }
  return response.json() as Promise<T>;
}
