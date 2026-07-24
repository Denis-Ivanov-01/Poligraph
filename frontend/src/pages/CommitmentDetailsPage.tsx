import { useState } from "react";
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

type CommitmentAnalysisItem = {
  key: string;
  label: string;
  value?: string | null;
  explanation?: string | null;
};

function displayValue(value?: string | null) {
  return value?.trim() || text.common.notAvailable;
}

function CommitmentAnalysisPanel({ title, items }: { title: string; items: CommitmentAnalysisItem[] }) {
  const visibleItems = items.filter((item) => item.value || item.explanation);
  const [activeKey, setActiveKey] = useState(visibleItems[0]?.key ?? "");
  const [lockedKey, setLockedKey] = useState<string | null>(null);
  const activeItem = visibleItems.find((item) => item.key === activeKey) ?? visibleItems[0];

  if (!visibleItems.length || !activeItem) return null;

  function previewItem(key: string) {
    if (!lockedKey) {
      setActiveKey(key);
    }
  }

  function selectItem(key: string) {
    if (lockedKey === key) {
      setLockedKey(null);
      return;
    }

    setActiveKey(key);
    setLockedKey(key);
  }

  return (
    <section className="content-panel commitment-analysis-panel">
      <h2>{title}</h2>
      <div className="score-grid score-grid-featured score-grid-interactive commitment-analysis-grid" aria-label={title}>
        {visibleItems.map((item) => (
          <button
            className={[
              "score-item",
              "score-trigger",
              activeItem.key === item.key ? "score-item-active" : "",
              lockedKey === item.key ? "score-item-locked" : ""
            ].filter(Boolean).join(" ")}
            key={item.key}
            type="button"
            aria-pressed={lockedKey === item.key}
            onClick={() => selectItem(item.key)}
            onFocus={() => previewItem(item.key)}
            onMouseEnter={() => previewItem(item.key)}
          >
            <span className="score-label">{item.label}</span>
            <strong className="commitment-analysis-value">{displayValue(item.value)}</strong>
          </button>
        ))}
      </div>
      <div className="explanation-panel" aria-live="polite" key={activeItem.key}>
        <p className="eyebrow">{text.analysis.explanations}</p>
        <h3>{activeItem.label}</h3>
        <p>{displayValue(activeItem.explanation || activeItem.value)}</p>
      </div>
    </section>
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
  const fulfillmentItems: CommitmentAnalysisItem[] = [
    {
      key: "status",
      label: text.analysis.status,
      value: commitment.status_label,
      explanation: commitment.status_explanation
    },
    {
      key: "confidence",
      label: text.programs.confidenceFilter,
      value: commitment.confidence_label,
      explanation: commitment.confidence_explanation
    },
    {
      key: "measurableCriteria",
      label: text.programs.measurableCriteria,
      value: commitment.measurable_criteria,
      explanation: commitment.measurable_criteria
    },
    {
      key: "measureValidity",
      label: text.programs.measureValidity,
      value: commitment.measure_validity_label,
      explanation: commitment.measurable_criteria
    }
  ];
  const contributionItems: CommitmentAnalysisItem[] = [
    {
      key: "contribution",
      label: text.programs.contribution,
      value: commitment.contribution_label,
      explanation: commitment.contribution_explanation
    },
    {
      key: "contributionConfidence",
      label: text.programs.contributionConfidence,
      value: commitment.contribution_confidence_label,
      explanation: commitment.contribution_explanation
    },
    {
      key: "controlLevel",
      label: text.programs.controlLevel,
      value: commitment.control_level_label,
      explanation: commitment.control_level_label
    },
    {
      key: "contributionTypes",
      label: text.programs.contributionTypes,
      value: commitment.contribution_types,
      explanation: commitment.contribution_types
    }
  ];
  const contextItems: CommitmentAnalysisItem[] = [
    {
      key: "responsibleInstitutions",
      label: text.programs.responsibleInstitutions,
      value: commitment.responsible_institutions,
      explanation: commitment.responsible_institutions
    },
    {
      key: "externalActors",
      label: text.programs.externalActors,
      value: commitment.required_external_actors,
      explanation: commitment.required_external_actors
    },
    {
      key: "baselineMode",
      label: text.programs.baselineMode,
      value: commitment.baseline_mode_label,
      explanation: commitment.baseline_mode_label
    },
    {
      key: "evaluationBasis",
      label: text.programs.evaluationBasis,
      value: commitment.evaluation_basis,
      explanation: commitment.evaluation_basis
    },
    {
      key: "quantitativeTarget",
      label: text.programs.quantitativeTarget,
      value: commitment.quantitative_target,
      explanation: commitment.quantitative_target
    },
    {
      key: "quantitativeActual",
      label: text.programs.quantitativeActual,
      value: commitment.quantitative_actual,
      explanation: commitment.quantitative_actual
    },
    {
      key: "officialProgramChange",
      label: text.programs.officialProgramChange,
      value: commitment.official_program_change_note,
      explanation: commitment.official_program_change_note
    },
    {
      key: "sourceVersionNote",
      label: text.programs.sourceVersionNote,
      value: commitment.source_version_note,
      explanation: commitment.source_version_note
    }
  ];

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

      <CommitmentAnalysisPanel title={text.programs.fulfillmentStatus} items={fulfillmentItems} />
      <CommitmentAnalysisPanel title={text.programs.cabinetContribution} items={contributionItems} />
      <CommitmentAnalysisPanel title={text.programs.evaluationContext} items={contextItems} />

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
