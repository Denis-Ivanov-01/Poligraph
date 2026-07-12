import { Link, useLocation, useParams } from "react-router-dom";

import { getCommitment, getCommitmentBySlug } from "../api/programs";
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

function EvidenceFlagList({ item }: { item: NonNullable<Commitment["evidence"]>[number] }) {
  const flags = [
    item.evidence_role_label,
    item.evidence_strength_label,
    item.is_self_reported ? text.programs.selfReported : null,
    item.is_independent_confirmation ? text.programs.independentConfirmation : null,
    item.is_contradictory ? text.programs.contradictoryEvidence : null,
    item.is_disproven ? text.programs.disprovenEvidence : null
  ].filter(Boolean);
  if (!flags.length) return null;
  return <span>{flags.join(` ${text.common.separator} `)}</span>;
}

function AiRunMetadataPanel({ metadata }: { metadata?: Commitment["analysis_metadata"] }) {
  if (!metadata) return null;
  return (
    <section className="content-panel">
      <h2>{text.analysis.transparencyTitle}</h2>
      <div className="commitment-detail-grid">
        <DetailRow label={text.analysis.usedModel} value={metadata.model_name} />
        <DetailRow label={text.analysis.promptVersion} value={metadata.prompt_version} />
        <DetailRow label={text.analysis.schemaVersionLong} value={metadata.schema_version} />
        <DetailRow label={text.programs.methodologyVersion} value={metadata.methodology_version} />
        <DetailRow label={text.analysis.analysisDate} value={metadata.analysis_date} />
        <DetailRow label={text.analysis.status} value={metadata.status} />
      </div>
    </section>
  );
}

function CommitmentDetail({ commitment }: { commitment: Commitment }) {
  const location = useLocation();
  return (
    <article className="commitment-detail">
      <div className="detail-hero">
        <p className="eyebrow">{commitment.program.title}</p>
        <h1>{commitment.title}</h1>
        <div className="commitment-card-badges">
          <span className={`status-badge status-${commitment.status}`}>{commitment.status_label}</span>
          {commitment.confidence_level && commitment.confidence_label ? (
            <span className={`confidence-badge confidence-${commitment.confidence_level}`}>{commitment.confidence_label}</span>
          ) : null}
          {commitment.contribution_label ? <span className="confidence-badge">{commitment.contribution_label}</span> : null}
        </div>
        <Link className="button-secondary" to={`/programs/${commitment.program.id}${location.search}`}>{text.programs.backToPrograms}</Link>
      </div>

      <section className="commitment-detail-grid">
        <DetailRow label={text.programs.topic} value={commitment.topic} />
        <DetailRow label={text.programs.deadline} value={commitment.deadline || commitment.period} />
        <DetailRow label={text.programs.lastUpdated} value={commitment.last_status_update} />
        <DetailRow label={text.programs.evidenceCount} value={String(commitment.evidence_count)} />
        <DetailRow label={text.programs.importance} value={commitment.importance_label} />
        <DetailRow label={text.programs.commitmentType} value={commitment.commitment_type_label} />
      </section>

      <AiRunMetadataPanel metadata={commitment.analysis_metadata} />

      <section className="content-panel">
        <h2>{text.programs.normalizedDescription}</h2>
        <p>{commitment.normalized_description || text.common.notAvailable}</p>
      </section>

      <section className="content-panel">
        <h2>{text.programs.originalText}</h2>
        <p className="statement-text">{commitment.original_text || text.common.notAvailable}</p>
      </section>

      <section className="analysis-split-panel">
        <div className="content-panel">
          <h2>{text.programs.fulfillmentStatus}</h2>
          <p><strong>{commitment.status_label}:</strong> {commitment.status_explanation || text.common.notAvailable}</p>
          {commitment.confidence_label ? <p><strong>{commitment.confidence_label}:</strong> {commitment.confidence_explanation || text.common.notAvailable}</p> : null}
          <p><strong>{text.programs.measurableCriteria}:</strong> {commitment.measurable_criteria || text.common.notAvailable}</p>
          <p><strong>{text.programs.measureValidity}:</strong> {commitment.measure_validity_label || text.common.notAvailable}</p>
        </div>
        <div className="content-panel">
          <h2>{text.programs.cabinetContribution}</h2>
          <p><strong>{commitment.contribution_label || text.common.notAvailable}:</strong> {commitment.contribution_explanation || text.common.notAvailable}</p>
          {commitment.contribution_confidence_label ? (
          <p><strong>{text.programs.contributionConfidence}:</strong> {commitment.contribution_confidence_label}</p>
          ) : null}
          <p><strong>{text.programs.controlLevel}:</strong> {commitment.control_level_label || text.common.notAvailable}</p>
          <p><strong>{text.programs.contributionTypes}:</strong> {commitment.contribution_types || text.common.notAvailable}</p>
        </div>
      </section>

      <section className="content-panel">
        <h2>{text.programs.evaluationContext}</h2>
        <p><strong>{text.programs.responsibleInstitutions}:</strong> {commitment.responsible_institutions || text.common.notAvailable}</p>
        <p><strong>{text.programs.externalActors}:</strong> {commitment.required_external_actors || text.common.notAvailable}</p>
        <p><strong>{text.programs.baselineMode}:</strong> {commitment.baseline_mode_label || text.common.notAvailable}</p>
        <p><strong>{text.programs.evaluationBasis}:</strong> {commitment.evaluation_basis || text.common.notAvailable}</p>
        <p><strong>{text.programs.quantitativeTarget}:</strong> {commitment.quantitative_target || text.common.notAvailable}</p>
        <p><strong>{text.programs.quantitativeActual}:</strong> {commitment.quantitative_actual || text.common.notAvailable}</p>
        {commitment.official_program_change_note ? <p><strong>{text.programs.officialProgramChange}:</strong> {commitment.official_program_change_note}</p> : null}
        {commitment.source_version_note ? <p><strong>{text.programs.sourceVersionNote}:</strong> {commitment.source_version_note}</p> : null}
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
                <span>{text.programs.evidenceRelation}: {item.relation_type}</span>
                <EvidenceFlagList item={item} />
                {item.claim ? <p><strong>{text.programs.evidenceClaim}:</strong> {item.claim}</p> : null}
                {item.accessed_at ? <span>{text.programs.sourceAccessed}: {item.accessed_at}</span> : null}
                {item.description ? <p>{item.description}</p> : null}
                {item.quote_or_relevant_excerpt ? <p>{item.quote_or_relevant_excerpt}</p> : null}
                {item.limitations ? <p>{item.limitations}</p> : null}
              </li>
            ))}
          </ul>
        ) : (
          <EmptyState message={text.programs.emptyEvidence} />
        )}
      </section>
      {commitment.status_history?.length ? (
        <section className="content-panel">
          <h2>{text.programs.statusHistory}</h2>
          <ul className="source-list">
            {commitment.status_history.map((item) => (
              <li key={`${item.created_at}-${item.new_status}`}>
                <strong>{text.programs.statuses[item.new_status as keyof typeof text.programs.statuses] || item.new_status}</strong>
                {item.contribution_label ? <span>{text.programs.contribution}: {item.contribution_label}</span> : null}
                <span>{item.effective_date || item.created_at}</span>
                {item.status_explanation ? <p>{item.status_explanation}</p> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </article>
  );
}

export function CommitmentDetailsPage() {
  const { programId, slug } = useParams();
  const { data, loading, error } = useAsync(
    () => {
      if (!slug) return Promise.resolve(null);
      return programId ? getCommitment(programId, slug) : getCommitmentBySlug(slug);
    },
    [programId, slug]
  );
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.programs.commitmentNotFound} />;
  return <CommitmentDetail commitment={data} />;
}
