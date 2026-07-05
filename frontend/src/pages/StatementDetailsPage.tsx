import { useParams } from "react-router-dom";
import type { ReactNode } from "react";

import { getStatementById } from "../api/statements";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { AiDetailsPanel } from "../components/statements/AiDetailsPanel";
import type { AiAnalysis } from "../types/aiAnalysis";
import type { Statement } from "../types/statement";
import { statementDisplayTitle } from "../utils/statements";
import { useAsync } from "../utils/useAsync";

function displayValue(value?: string | null) {
  return value?.trim() || text.analysis.notAvailable;
}

function TransparencySummaryItem({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{displayValue(value)}</strong>
    </div>
  );
}

function TransparencyPanel({
  title,
  children,
  raw = false
}: {
  title: string;
  children: ReactNode;
  raw?: boolean;
}) {
  return (
    <details className="statement-transparency__panel">
      <summary>{title}</summary>
      <div className={raw ? "statement-transparency__raw" : "statement-transparency__content"}>{children}</div>
    </details>
  );
}

function StatementTransparency({ statement, analysis }: { statement: Statement; analysis?: AiAnalysis | null }) {
  const sourceLabel = statement.source_url || text.analysis.notAvailable;
  const promptText = analysis?.ai_details?.prompt_text || text.analysis.notAvailable;
  const rawResponse = analysis?.ai_details?.raw_ai_response || text.analysis.notAvailable;

  return (
    <section className="statement-transparency">
      <div className="statement-transparency__header">
        <p className="eyebrow">{text.analysis.details}</p>
        <h2>{text.analysis.transparencyTitle}</h2>
        <p>{text.analysis.transparencyIntro}</p>
      </div>

      <div className="statement-transparency__summary">
        <TransparencySummaryItem label={text.analysis.usedModel} value={analysis?.model_name} />
        <TransparencySummaryItem label={text.analysis.promptVersion} value={analysis?.prompt_version} />
        <TransparencySummaryItem label={text.analysis.schemaVersionLong} value={analysis?.schema_version} />
        <TransparencySummaryItem label={text.analysis.analysisDate} value={analysis?.analysis_date} />
        <TransparencySummaryItem label={text.analysis.status} value={text.analysis.moderatorStatusUnavailable} />
      </div>

      <div className="statement-transparency__details">
        <div className="statement-transparency__source">
          <span>{text.analysis.originalSource}</span>
          {statement.source_url ? (
            <a href={statement.source_url} rel="noreferrer" target="_blank">{sourceLabel}</a>
          ) : (
            <strong>{sourceLabel}</strong>
          )}
        </div>

        <TransparencyPanel title={text.analysis.originalText}>
          <p>{statement.original_text || text.analysis.notAvailable}</p>
        </TransparencyPanel>

        <TransparencyPanel title={text.analysis.modelInstruction} raw>
          <pre>{promptText}</pre>
        </TransparencyPanel>

        <TransparencyPanel title={text.analysis.rawModelResponse} raw>
          <pre>{rawResponse}</pre>
        </TransparencyPanel>

        <TransparencyPanel title={text.analysis.moderatorReview}>
          <p>{text.analysis.moderatorReviewText}</p>
          <p><strong>{text.analysis.status}:</strong> {text.analysis.moderatorStatusUnavailable}</p>
        </TransparencyPanel>
      </div>
    </section>
  );
}

export function StatementDetailsPage() {
  const { id = "" } = useParams();
  const { data, loading, error } = useAsync(() => getStatementById(id), [id]);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.statements.notFound} />;
  return (
    <article className="section detail">
      <header className="detail-hero">
        <p className="eyebrow">{data.statement_date ?? text.common.noDate} {text.common.separator} {data.source_type}</p>
        <h1>{statementDisplayTitle(data)}</h1>
        <p className="muted">
          {data.politician.full_name}
          {data.party_at_statement_time ? `, ${data.party_at_statement_time.full_name}` : ""}
        </p>
        {data.source_url ? <a className="button-secondary" href={data.source_url} rel="noreferrer" target="_blank">{text.common.source}</a> : null}
      </header>
      <section className="content-panel">
        <h2>{text.statements.original}</h2>
        <p className="statement-text">{data.original_text}</p>
      </section>
      {data.ai_analysis ? (
        <AiDetailsPanel analysis={data.ai_analysis} />
      ) : (
        <EmptyState message={text.statements.noAnalysis} />
      )}
      <StatementTransparency statement={data} analysis={data.ai_analysis} />
    </article>
  );
}
