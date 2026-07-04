import resources from "../resources.json";

export const text = resources;

export function formatResource(template: string, values: Record<string, string | number | null | undefined>) {
  return template.replace(/\{(\w+)\}/g, (_, key: string) => String(values[key] ?? ""));
}
