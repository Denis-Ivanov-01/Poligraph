import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { getCommitments, getPrograms } from "../api/programs";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { text } from "../i18n/resources";
import type { Commitment, Program } from "../types/program";
import { useAsync } from "../utils/useAsync";

function StatusBadge({ commitment }: { commitment: Commitment }) {
  return <span className={`status-badge status-${commitment.status}`}>{commitment.status_label}</span>;
}

function ConfidenceBadge({ commitment }: { commitment: Commitment }) {
  return <span className={`confidence-badge confidence-${commitment.confidence_level}`}>{commitment.confidence_label}</span>;
}

function CommitmentCard({ commitment }: { commitment: Commitment }) {
  return (
    <Link className="commitment-card" to={`/programs/commitments/${commitment.slug}`}>
      <article>
        <div className="commitment-card-main">
          <div className="commitment-card-badges">
            <StatusBadge commitment={commitment} />
            <ConfidenceBadge commitment={commitment} />
          </div>
          <h3>{commitment.title}</h3>
          <p>{commitment.normalized_description || commitment.original_text}</p>
          <div className="commitment-meta">
            <span>{commitment.topic || text.common.notAvailable}</span>
            <span>{commitment.program.title}</span>
            <span>{commitment.evidence_count} {text.programs.evidenceShort}</span>
          </div>
        </div>
        <span className="commitment-open">{text.programs.openDetails}</span>
      </article>
    </Link>
  );
}

function ActiveProgramCard({ program }: { program?: Program }) {
  if (!program) return null;
  return (
    <section className="program-active-card">
      <p className="eyebrow">{text.programs.activeGovernmentProgram}</p>
      <h2>{program.title}</h2>
      <p>{program.description || program.political_subject_name}</p>
      <div className="commitment-meta">
        <span>{program.program_type_label}</span>
        <span>{program.political_subject_name}</span>
        {program.source_url ? (
          <a href={program.source_url} target="_blank" rel="noreferrer">
            {text.common.source}
          </a>
        ) : null}
      </div>
    </section>
  );
}

export function ProgramsPage() {
  const [status, setStatus] = useState("");
  const [topic, setTopic] = useState("");
  const [programId, setProgramId] = useState("");
  const [keyOnly, setKeyOnly] = useState(false);
  const { data: programs, loading: programsLoading, error: programsError } = useAsync(getPrograms, []);
  const { data, loading, error } = useAsync(
    () => getCommitments({ status, topic, program_id: programId, key_only: keyOnly }),
    [status, topic, programId, keyOnly]
  );
  const activeProgram = useMemo(() => programs?.find((program) => program.is_active_government_program), [programs]);
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    data?.items.forEach((commitment) => {
      counts[commitment.status] = (counts[commitment.status] ?? 0) + 1;
    });
    return counts;
  }, [data]);

  return (
    <section className="section programs-page">
      <div className="page-hero">
        <div className="hero-copy">
          <p className="eyebrow">{text.programs.eyebrow}</p>
          <h1>{text.programs.title}</h1>
          <p className="hero-subtitle">{text.programs.subtitle}</p>
        </div>
      </div>

      {programsLoading ? <LoadingState /> : null}
      {programsError ? <ErrorState message={programsError} /> : null}
      <ActiveProgramCard program={activeProgram} />

      <section className="program-status-summary" aria-label={text.programs.statusSummary}>
        {Object.entries(text.programs.statuses).map(([key, label]) => (
          <div key={key}>
            <span>{statusCounts[key] ?? 0}</span>
            <small>{label}</small>
          </div>
        ))}
      </section>

      <section className="program-filters">
        <label>
          {text.programs.filters.status}
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">{text.programs.filters.all}</option>
            {Object.entries(text.programs.statuses).map(([key, label]) => (
              <option value={key} key={key}>{label}</option>
            ))}
          </select>
        </label>
        <label>
          {text.programs.filters.topic}
          <select value={topic} onChange={(event) => setTopic(event.target.value)}>
            <option value="">{text.programs.filters.all}</option>
            {data?.topics.map((item) => (
              <option value={item} key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label>
          {text.programs.filters.program}
          <select value={programId} onChange={(event) => setProgramId(event.target.value)}>
            <option value="">{text.programs.filters.all}</option>
            {programs?.map((program) => (
              <option value={program.id} key={program.id}>{program.title}</option>
            ))}
          </select>
        </label>
        <label className="filter-checkbox">
          <input type="checkbox" checked={keyOnly} onChange={(event) => setKeyOnly(event.target.checked)} />
          {text.programs.filters.keyOnly}
        </label>
      </section>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? (
        data?.items.length ? (
          <div className="commitment-grid">
            {data.items.map((commitment) => (
              <CommitmentCard commitment={commitment} key={commitment.id} />
            ))}
          </div>
        ) : (
          <EmptyState message={text.programs.emptyCommitments} />
        )
      ) : null}
    </section>
  );
}
