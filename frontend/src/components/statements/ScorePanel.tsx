import type { AiScores } from "../../types/aiAnalysis";
import { text } from "../../i18n/resources";
import { ScoreBadge } from "../common/ScoreBadge";

const labels: Record<keyof AiScores, string> = {
  factual_accuracy: text.scores.factualAccuracy,
  logical_consistency: text.scores.logicalConsistency,
  communicational_integrity: text.scores.communicationalIntegrity,
  principle_consistency: text.scores.principleConsistency,
  overall: text.scores.overall
};

export function ScorePanel({ scores }: { scores: AiScores }) {
  return (
    <dl className="score-grid">
      {(Object.keys(labels) as Array<keyof AiScores>).map((key) => (
        <div className={key === "overall" ? "score-item score-item-featured" : "score-item"} key={key}>
          <dt>{labels[key]}</dt>
          <dd><ScoreBadge value={scores[key]} size={key === "overall" ? "large" : "medium"} /></dd>
        </div>
      ))}
    </dl>
  );
}
