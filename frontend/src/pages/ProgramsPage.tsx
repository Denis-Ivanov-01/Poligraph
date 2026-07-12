import { Link } from "react-router-dom";

import { getPrograms } from "../api/programs";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { text } from "../i18n/resources";
import type { Program } from "../types/program";
import { useAsync } from "../utils/useAsync";

const STATUS_KEYS = [
  "fulfilled",
  "kept_to_date",
  "in_progress",
  "delayed",
  "partially_fulfilled",
  "violated",
  "not_started",
  "condition_not_met",
  "not_due",
  "not_applicable",
  "unclear",
  "abandoned",
  "not_analyzed"
];

function ProgramStatusCounts({ counts }: { counts?: Record<string, number> }) {
  return (
    <div className="program-tile-statuses">
      {STATUS_KEYS.map((key) => (
        <div key={key}>
          <span>{counts?.[key] ?? 0}</span>
          <small>{text.programs.statuses[key as keyof typeof text.programs.statuses]}</small>
        </div>
      ))}
    </div>
  );
}

function ProgramTile({ program }: { program: Program }) {
  return (
    <Link className="program-tile" to={`/programs/${program.id}`}>
      <article>
        <div className="program-tile-main">
          <p className="eyebrow">{program.is_active_government_program ? text.programs.activeGovernmentProgram : program.program_type_label}</p>
          <h2>{program.title}</h2>
          <p>{program.short_description || program.description || program.political_subject_name}</p>
        </div>
        <ProgramStatusCounts counts={program.status_counts} />
        <div className="commitment-meta">
          <span>{program.political_subject_name}</span>
          <span>{program.period_text || text.common.noDate}</span>
          <span>{program.total_commitments ?? 0} {text.programs.totalCommitments}</span>
        </div>
        <span className="commitment-open">{text.programs.openProgram}</span>
      </article>
    </Link>
  );
}

export function ProgramsPage() {
  const { data: programs, loading, error } = useAsync(getPrograms, []);

  return (
    <section className="section programs-page">
      <div className="page-hero">
        <div className="hero-copy">
          <p className="eyebrow">{text.programs.eyebrow}</p>
          <h1>{text.programs.title}</h1>
          <p className="hero-subtitle">{text.programs.subtitle}</p>
        </div>
      </div>

      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? (
        programs?.length ? (
          <div className="program-tile-grid">
            {programs.map((program) => (
              <ProgramTile program={program} key={program.id} />
            ))}
          </div>
        ) : (
          <EmptyState message={text.programs.emptyPrograms} />
        )
      ) : null}
    </section>
  );
}
