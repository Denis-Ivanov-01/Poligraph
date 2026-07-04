import { useState } from "react";

import type { AiAnalysis, AiScores } from "../../types/aiAnalysis";
import { text } from "../../i18n/resources";
import { ScorePanel, scoreLabels } from "./ScorePanel";

export function AiDetailsPanel({ analysis }: { analysis: AiAnalysis }) {
  const [activeExplanation, setActiveExplanation] = useState<keyof AiScores>("overall");
  const [lockedExplanation, setLockedExplanation] = useState<keyof AiScores | null>(null);

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
        scores={analysis.scores}
      />
      <div className="explanation-panel" aria-live="polite" key={activeExplanation}>
        <p className="eyebrow">{text.analysis.explanations}</p>
        <h3>{scoreLabels[activeExplanation]}</h3>
        <p>{analysis.explanations[activeExplanation]}</p>
      </div>
      {analysis.source_urls.length ? (
        <div className="source-panel">
          <h3>{text.analysis.sourceUrls}</h3>
          <ul className="source-list">
            {analysis.source_urls.map((source) => (
              <li key={source.url}>
                <a href={source.url}>{source.description || source.url}</a>
                {source.description ? <span>{source.url}</span> : null}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      <details>
        <summary>{text.analysis.details}</summary>
        <p>{text.analysis.model}: {analysis.model_name}</p>
        <p>{text.analysis.promptVersion}: {analysis.prompt_version}</p>
        <p>{text.analysis.schemaVersion}: {analysis.schema_version}</p>
        <pre>{analysis.ai_details.prompt_text}</pre>
        <pre>{analysis.ai_details.raw_ai_response}</pre>
      </details>
    </section>
  );
}
