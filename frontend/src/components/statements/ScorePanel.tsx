import type { AiScores } from "../../types/aiAnalysis";
import { text } from "../../i18n/resources";
import { ScoreBadge } from "../common/ScoreBadge";

export const scoreLabels: Record<keyof AiScores, string> = {
  factual_accuracy: text.scores.factualAccuracy,
  logical_consistency: text.scores.logicalConsistency,
  communicational_integrity: text.scores.communicationalIntegrity,
  principle_consistency: text.scores.principleConsistency,
  overall: text.scores.overall
};

type ScorePanelProps = {
  scores: AiScores;
  activeScore?: keyof AiScores;
  lockedScore?: keyof AiScores | null;
  variant?: "default" | "featured";
  onScoreSelect?: (key: keyof AiScores) => void;
  onScorePreview?: (key: keyof AiScores) => void;
};

export function ScorePanel({
  scores,
  activeScore,
  lockedScore,
  variant = "default",
  onScoreSelect,
  onScorePreview
}: ScorePanelProps) {
  if (onScoreSelect) {
    return (
      <div className="score-grid score-grid-featured score-grid-interactive" aria-label={text.analysis.explanations}>
        {(Object.keys(scoreLabels) as Array<keyof AiScores>).map((key) => (
          <button
            className={[
              "score-item",
              "score-trigger",
              key === "overall" ? "score-item-featured" : "",
              activeScore === key ? "score-item-active" : "",
              lockedScore === key ? "score-item-locked" : ""
            ].filter(Boolean).join(" ")}
            key={key}
            type="button"
            aria-pressed={lockedScore === key}
            onClick={() => onScoreSelect(key)}
            onFocus={() => onScorePreview?.(key)}
            onMouseEnter={() => onScorePreview?.(key)}
          >
            <span className="score-label">{scoreLabels[key]}</span>
            <ScoreBadge value={scores[key] ?? undefined} size={key === "overall" ? "large" : "medium"} />
          </button>
        ))}
      </div>
    );
  }

  return (
    <dl className={variant === "featured" ? "score-grid score-grid-featured" : "score-grid"}>
      {(Object.keys(scoreLabels) as Array<keyof AiScores>).map((key) => (
        <div
          className={[
            "score-item",
            key === "overall" ? "score-item-featured" : "",
            activeScore === key ? "score-item-active" : ""
          ].filter(Boolean).join(" ")}
          key={key}
        >
          <dt>{scoreLabels[key]}</dt>
          <dd>
            <ScoreBadge value={scores[key] ?? undefined} size={key === "overall" ? "large" : "medium"} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
