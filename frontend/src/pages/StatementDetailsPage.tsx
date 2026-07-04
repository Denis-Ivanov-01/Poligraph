import { useParams } from "react-router-dom";

import { getStatementById } from "../api/statements";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { AiDetailsPanel } from "../components/statements/AiDetailsPanel";
import { statementDisplayTitle } from "../utils/statements";
import { useAsync } from "../utils/useAsync";

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
        {data.source_url ? <a className="button-secondary" href={data.source_url}>{text.common.source}</a> : null}
      </header>
      <section className="content-panel">
        <h2>{text.statements.original}</h2>
        <p className="statement-text">{data.original_text}</p>
      </section>
      {data.ai_analysis ? <AiDetailsPanel analysis={data.ai_analysis} /> : <EmptyState message={text.statements.noAnalysis} />}
    </article>
  );
}
