import { apiGet } from "./client";
import type { Dashboard } from "../types/dashboard";

export function getDashboard() {
  return apiGet<Dashboard>("/dashboard");
}
