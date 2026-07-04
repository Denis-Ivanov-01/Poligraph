type ScoreBadgeSize = "small" | "medium" | "large";

function scoreClass(value: number): string {
  if (value >= 90) return "score-90";
  if (value >= 80) return "score-80";
  if (value >= 70) return "score-70";
  if (value >= 60) return "score-60";
  if (value >= 50) return "score-50";
  if (value >= 40) return "score-40";
  return "score-0";
}

export function ScoreBadge({ value, size = "medium" }: { value?: number | null; size?: ScoreBadgeSize }) {
  if (value === null || value === undefined) {
    return <span className={`score-badge score-empty score-${size}`}>-</span>;
  }
  const rounded = Math.round(value);
  return <span className={`score-badge ${scoreClass(rounded)} score-${size}`}>{rounded}</span>;
}
