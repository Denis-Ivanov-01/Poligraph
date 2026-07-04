import type { AiAnalysis } from "../../types/aiAnalysis";
import { text } from "../../i18n/resources";
import { ScorePanel } from "./ScorePanel";

export function AiDetailsPanel({ analysis }: { analysis: AiAnalysis }) {
  return (
    <section className="section">
      <h2>{text.analysis.title}</h2>
      <ScorePanel scores={analysis.scores} />
      <div className="explanations">
        <h3>{text.analysis.explanations}</h3>
        <p><strong>{text.scores.factualAccuracy}:</strong> {analysis.explanations.factual_accuracy}</p>
        <p><strong>{text.scores.logicalConsistency}:</strong> {analysis.explanations.logical_consistency}</p>
        <p><strong>{text.scores.communicationalIntegrity}:</strong> {analysis.explanations.communicational_integrity}</p>
        <p><strong>{text.scores.principleConsistency}:</strong> {analysis.explanations.principle_consistency}</p>
        <p><strong>{text.scores.overall}:</strong> {analysis.explanations.overall}</p>
      </div>
      {analysis.source_urls.length ? (
        <div className="explanations">
          <h3>{text.analysis.sourceUrls}</h3>
          <ul>
            {analysis.source_urls.map((source) => (
              <li key={source.url}>
                <a href={source.url}>{source.url}</a>
                {source.description ? ` - ${source.description}` : ""}
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
