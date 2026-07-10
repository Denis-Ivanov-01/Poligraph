import { useState } from "react";

import type { AiAnalysis, AiScores } from "../../types/aiAnalysis";
import { text } from "../../i18n/resources";
import { ScorePanel, scoreLabels } from "./ScorePanel";

export function AiDetailsPanel({ analysis }: { analysis: AiAnalysis }) {
  const [activeExplanation, setActiveExplanation] = useState<keyof AiScores>("overall");
  const [lockedExplanation, setLockedExplanation] = useState<keyof AiScores | null>(null);
  const scores = withComputedOverall(analysis.scores);

  function previewExplanation(score: keyof AiScores) {
    if (!lockedExplanation) {
      setActiveExplanation(score);
    }
  }

  function selectExplanation(score: keyof AiScores) {
    if (lockedExplanation === score) {
      setLockedExplanation(null);
      return;
    }

    setActiveExplanation(score);
    setLockedExplanation(score);
  }

  return (
    <section className="section analysis-panel">
      <h2>{text.analysis.title}</h2>
      <ScorePanel
        activeScore={activeExplanation}
        lockedScore={lockedExplanation}
        onScorePreview={previewExplanation}
        onScoreSelect={selectExplanation}
        scores={scores}
      />
      <div className="explanation-panel" aria-live="polite" key={activeExplanation}>
        <p className="eyebrow">{text.analysis.explanations}</p>
        <h3>{scoreLabels[activeExplanation]}</h3>
        <p>{activeExplanation === "overall" ? "Computed in the interface as the average of the four dimension scores." : analysis.explanations[activeExplanation]}</p>
      </div>
      {analysis.disclaimer ? <p className="analysis-disclaimer">{analysis.disclaimer}</p> : null}
      {analysis.claims?.length ? (
        <div className="source-panel">
          <h3>Extracted claims</h3>
          <ul className="source-list">
            {analysis.claims.map((claim) => (
              <li key={claim.id}>
                <strong>{claim.display_code || claim.claim_type}: {claim.normalized_claim}</strong>
                <span>Materiality: {claim.materiality}; AI verification status: {claim.ai_verification_status}; confidence: {claim.confidence_level}</span>
                {claim.sources?.length ? (
                  <ul>
                    {claim.sources.map((source) => (
                      <li key={`${claim.id}-${source.url}`}>
                        <a href={source.url} rel="noreferrer" target="_blank">{source.description || source.url}</a>
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {analysis.source_urls.length ? (
        <div className="source-panel">
          <h3>{text.analysis.sourceUrls}</h3>
          <ul className="source-list">
            {analysis.source_urls.map((source) => (
              <li key={source.url}>
                <a href={source.url} rel="noreferrer" target="_blank">{source.description || source.url}</a>
                {source.description ? <span>{source.url}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

function withComputedOverall(scores: AiScores): AiScores {
  const values = [
    scores.factual_accuracy,
    scores.logical_consistency,
    scores.communicational_integrity,
    scores.principle_consistency
  ].filter((value): value is number => typeof value === "number");

  return {
    ...scores,
    overall: values.length ? Math.round(values.reduce((sum, value) => sum + value, 0) / values.length) : null
  };
}
