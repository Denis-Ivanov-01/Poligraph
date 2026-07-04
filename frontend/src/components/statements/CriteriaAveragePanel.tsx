import type { CriteriaAverages } from "../../types/aiAnalysis";
import { ScorePanel } from "./ScorePanel";

export function CriteriaAveragePanel({ scores }: { scores: CriteriaAverages }) {
  return <ScorePanel scores={scores} variant="featured" />;
}
