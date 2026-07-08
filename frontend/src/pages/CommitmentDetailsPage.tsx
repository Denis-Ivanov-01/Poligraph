import { Link, useParams } from "react-router-dom";

import { getCommitment } from "../api/programs";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { text } from "../i18n/resources";
import type { Commitment } from "../types/program";
import { useAsync } from "../utils/useAsync";

function DetailRow({ label, value }: { label: string; value?: string | null }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value || text.common.notAvailable}</strong>
    </div>
  );
}

function CommitmentDetail({ commitment }: { commitment: Commitment }) {
  return (
    <article className="commitment-detail">
      <div className="detail-hero">
        <p className="eyebrow">{commitment.program.title}</p>
        <h1>{commitment.title}</h1>
        <div className="commitment-card-badges">
          <span className={`status-badge status-${commitment.status}`}>{commitment.status_label}</span>
          <span className={`confidence-badge confidence-${commitment.confidence_level}`}>{commitment.confidence_label}</span>
        </div>
        <Link className="button-secondary" to="/programs">{text.programs.backToPrograms}</Link>
      </div>

      <section className="commitment-detail-grid">
        <DetailRow label={text.programs.topic} value={commitment.topic} />
        <DetailRow label={text.programs.deadline} value={commitment.deadline || commitment.period} />
        <DetailRow label={text.programs.lastUpdated} value={commitment.last_status_update} />
        <DetailRow label={text.programs.evidenceCount} value={String(commitment.evidence_count)} />
      </section>

      <section className="content-panel">
        <h2>{text.programs.normalizedDescription}</h2>
        <p>{commitment.normalized_description || text.common.notAvailable}</p>
      </section>

      <section className="content-panel">
        <h2>{text.programs.originalText}</h2>
        <p className="statement-text">{commitment.original_text || text.common.notAvailable}</p>
      </section>

      <section className="content-panel">
        <h2>{text.programs.statusAndConfidence}</h2>
        <p><strong>{commitment.status_label}:</strong> {commitment.status_explanation || text.common.notAvailable}</p>
        <p><strong>{commitment.confidence_label}:</strong> {commitment.confidence_explanation || text.common.notAvailable}</p>
        <p><strong>{text.programs.measurableCriteria}:</strong> {commitment.measurable_criteria || text.common.notAvailable}</p>
        <p><strong>{text.programs.responsibleInstitutions}:</strong> {commitment.responsible_institutions || text.common.notAvailable}</p>
      </section>

      <section className="source-panel">
        <h2>{text.programs.evidence}</h2>
        {commitment.evidence?.length ? (
          <ul className="source-list">
            {commitment.evidence.map((item) => (
              <li key={item.id}>
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
                ) : (
                  <strong>{item.title}</strong>
                )}
                <span>{item.source_type_label}{item.publisher ? ` ${text.common.separator} ${item.publisher}` : ""}</span>
                {item.description ? <p>{item.description}</p> : null}
                {item.quote_or_relevant_excerpt ? <p>{item.quote_or_relevant_excerpt}</p> : null}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message={text.programs.emptyEvidence} />
        )}
      </section>
    </article>
  );
}

export function CommitmentDetailsPage() {
  const { slug } = useParams();
  const { data, loading, error } = useAsync(() => (slug ? getCommitment(slug) : Promise.resolve(null)), [slug]);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.programs.commitmentNotFound} />;
  return <CommitmentDetail commitment={data} />;
}
