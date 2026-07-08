import { Link } from "react-router-dom";

import { getDashboard } from "../api/dashboard";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { MetricIcon } from "../components/common/MetricIcon";
import { ScoreBadge } from "../components/common/ScoreBadge";
import { StatementCard } from "../components/statements/StatementCard";
import { scoreLabels } from "../components/statements/ScorePanel";
import type { Dashboard, DashboardRankingItem } from "../types/dashboard";
import type { ActiveGovernmentProgramSummary } from "../types/program";
import type { StatementListItem } from "../types/statement";
import { statementDisplayTitle } from "../utils/statements";
import { useAsync } from "../utils/useAsync";

function HomeHero({ data }: { data: Dashboard }) {
  return (
    <section className="home-hero">
      <div className="home-hero-copy">
        <p className="eyebrow">{text.home.heroEyebrow}</p>
        <h1>{text.home.heroHeading}</h1>
        <p className="hero-subtitle">{text.home.heroSubtitle}</p>
        <div className="hero-actions">
          <Link className="button-primary" to="/statements">{text.home.browseStatements}</Link>
          <a className="button-secondary" href="#methodology-preview">{text.home.readMethodology}</a>
          <Link className="button-secondary" to="/dashboard">{text.home.viewDashboard}</Link>
        </div>
        <div className="trust-badges" aria-label={text.home.trustBadgesAria}>
          <span>{text.home.aiPoweredAnalysis}</span>
          <span>{text.home.transparentMethodology}</span>
          <span>{text.home.evidenceBasedEvaluation}</span>
        </div>
      </div>
      <StatementPreview statement={data.latest_statements[0]} />
    </section>
  );
}

function StatementPreview({ statement }: { statement?: StatementListItem }) {
  if (!statement) {
    return (
      <div className="home-preview-card home-preview-empty">
        <p className="eyebrow">{text.home.previewEyebrow}</p>
        <h2>{text.home.previewEmptyTitle}</h2>
        <p>{text.home.previewEmptyText}</p>
      </div>
    );
  }

  return (
    <Link className="home-preview-card" to={`/statements/${statement.id}`}>
      <p className="eyebrow">{text.home.previewEyebrow}</p>
      <h2>{statementDisplayTitle(statement)}</h2>
      <p className="preview-meta">
        {statement.politician.full_name}
        {statement.party_at_statement_time ? `, ${statement.party_at_statement_time.short_name}` : ""}
      </p>
      <div className="preview-score">
        <span>{text.scores.overall}</span>
        <ScoreBadge value={statement.overall_score} size="large" />
      </div>
      <span className="preview-link">{text.home.openAnalysis}</span>
    </Link>
  );
}

function HomeNavigationCards() {
  const cards = [
    {
      icon: "statements" as const,
      title: text.home.navStatementsTitle,
      description: text.home.navStatementsDescription,
      cta: text.home.browseStatements,
      to: "/statements"
    },
    {
      icon: "politicians" as const,
      title: text.home.navPoliticiansTitle,
      description: text.home.navPoliticiansDescription,
      cta: text.home.browsePoliticians,
      to: "/politicians"
    },
    {
      icon: "parties" as const,
      title: text.home.navPartiesTitle,
      description: text.home.navPartiesDescription,
      cta: text.home.browseParties,
      to: "/parties"
    }
  ];

  return (
    <section className="home-section">
      <div className="home-card-grid">
        {cards.map((card) => (
          <Link className="home-nav-card" to={card.to} key={card.to}>
            <MetricIcon type={card.icon} />
            <h2>{card.title}</h2>
            <p>{card.description}</p>
            <span>{card.cta}</span>
          </Link>
        ))}
      </div>
    </section>
  );
}

function HomeRankings({ data }: { data: Dashboard }) {
  return (
    <section className="home-section" id="home-rankings">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.home.rankingsEyebrow}</p>
          <h2>{text.home.rankingsTitle}</h2>
        </div>
        <Link to="/dashboard">{text.home.viewDashboard}</Link>
      </div>
      <div className="home-ranking-grid">
        <RankingPanel
          title={text.home.topPoliticiansTitle}
          emptyMessage={text.home.emptyPoliticianRankings}
          items={data.top_politicians}
          pathPrefix="/politicians"
        />
        <RankingPanel
          title={text.home.topPartiesTitle}
          emptyMessage={text.home.emptyPartyRankings}
          items={data.top_parties}
          pathPrefix="/parties"
        />
      </div>
      <p className="home-note">{text.home.rankingsNote}</p>
    </section>
  );
}

function RankingPanel({
  title,
  emptyMessage,
  items,
  pathPrefix
}: {
  title: string;
  emptyMessage: string;
  items: DashboardRankingItem[];
  pathPrefix: "/politicians" | "/parties";
}) {
  return (
    <div className="home-ranking-panel">
      <h3>{title}</h3>
      {items.length ? (
        <ol className="home-ranking-list">
          {items.map((item, index) => (
            <li key={item.id}>
              <Link to={`${pathPrefix}/${item.slug}`}>
                <span className="rank-number">{index + 1}</span>
                <span className="rank-content">
                  <strong>{item.full_name}</strong>
                  <small>
                    {item.short_name ? `${item.short_name} ${text.common.separator} ` : ""}
                    {item.analyzed_statement_count} {text.home.analyzedStatementsShort}
                  </small>
                </span>
                <ScoreBadge value={item.average_overall_score} size="medium" />
              </Link>
            </li>
          ))}
        </ol>
      ) : (
        <EmptyState message={emptyMessage} />
      )}
    </div>
  );
}

function HomeLatestStatements({ statements }: { statements: StatementListItem[] }) {
  return (
    <section className="home-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.home.latestEyebrow}</p>
          <h2>{text.home.latestTitle}</h2>
        </div>
        <Link to="/statements">{text.statements.browseAll}</Link>
      </div>
      {statements.length ? (
        <div className="list statement-list">
          {statements.slice(0, 4).map((statement) => (
            <StatementCard statement={statement} key={statement.id} />
          ))}
        </div>
      ) : (
        <EmptyState message={text.home.noPublishedYet} />
      )}
    </section>
  );
}

function HomeCommitmentsSummary({ summary }: { summary?: ActiveGovernmentProgramSummary | null }) {
  const counts = summary?.status_counts;
  const countItems = [
    ["fulfilled", text.programs.statuses.fulfilled],
    ["in_progress", text.programs.statuses.in_progress],
    ["partially_fulfilled", text.programs.statuses.partially_fulfilled],
    ["broken", text.programs.statuses.broken],
    ["not_started", text.programs.statuses.not_started],
    ["insufficient_data", text.programs.statuses.insufficient_data],
    ["blocked", text.programs.statuses.blocked],
    ["abandoned", text.programs.statuses.abandoned]
  ];

  return (
    <section className="home-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.programs.eyebrow}</p>
          <h2>{text.home.commitmentsTitle}</h2>
        </div>
        <Link to="/programs">{text.programs.viewAll}</Link>
      </div>
      {!summary ? (
        <EmptyState message={text.home.noActiveGovernmentProgram} />
      ) : (
        <div className="home-commitments-panel">
          <div className="home-commitments-intro">
            <p className="eyebrow">{summary.program.title}</p>
            <h3>{text.home.commitmentsQuestion}</h3>
            <p>{text.programs.subtitle}</p>
            <strong>{summary.total_commitments} {text.home.totalCommitments}</strong>
          </div>
          <div className="home-commitments-counts">
            {countItems.map(([key, label]) => (
              <div key={key}>
                <span>{counts?.[key] ?? 0}</span>
                <small>{label}</small>
              </div>
            ))}
          </div>
          {summary.key_commitments.length ? (
            <ul className="home-commitments-list">
              {summary.key_commitments.map((commitment) => (
                <li key={commitment.id}>
                  <Link to={`/programs/commitments/${commitment.slug}`}>
                    <strong>{commitment.title}</strong>
                    <span className={`status-badge status-${commitment.status}`}>{commitment.status_label}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message={text.home.noKeyCommitments} />
          )}
        </div>
      )}
    </section>
  );
}

function HomePurposePlaceholder() {
  return (
    <section className="home-editorial-panel">
      <div>
        <p className="eyebrow">{text.home.purposeEyebrow}</p>
        <h2>{text.home.purposeTitle}</h2>
        {text.home.purposeText.map((paragraph) => (
          <p key={paragraph}>{paragraph}</p>
        ))}
        <Link className="button-secondary" to="/methodology">{text.home.readMethodology}</Link>
      </div>
      <ul>
        {text.home.purposePrinciples.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function HomeMethodologyPreview() {
  const dimensions = [
    {
      label: scoreLabels.factual_accuracy,
      description: text.home.methodologyDimensions.factualAccuracy
    },
    {
      label: scoreLabels.logical_consistency,
      description: text.home.methodologyDimensions.logicalConsistency
    },
    {
      label: scoreLabels.communicational_integrity,
      description: text.home.methodologyDimensions.communicationalIntegrity
    },
    {
      label: scoreLabels.principle_consistency,
      description: text.home.methodologyDimensions.principleConsistency
    }
  ];

  return (
    <section className="home-section" id="methodology-preview">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.home.methodologyEyebrow}</p>
          <h2>{text.home.methodologyTitle}</h2>
        </div>
        <Link to="/methodology">{text.home.aboutMethodology}</Link>
      </div>
      <p className="home-section-lead">{text.home.methodologyLead}</p>
      <div className="home-method-grid">
        {dimensions.map((dimension) => (
          <article className="home-method-card" key={dimension.label}>
            <MetricIcon type="methodology" />
            <h3>{dimension.label}</h3>
            <p>{dimension.description}</p>
          </article>
        ))}
      </div>
      <aside className="home-transparency-note">
        <MetricIcon type="shield" />
        <div>
          <h3>{text.home.transparencyNoteTitle}</h3>
          <p>{text.home.transparencyNoteText}</p>
        </div>
      </aside>
    </section>
  );
}

function HomeNotEvaluatedPlaceholder() {
  return (
    <section className="home-section">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{text.home.notEvaluatedEyebrow}</p>
          <h2>{text.home.notEvaluatedTitle}</h2>
        </div>
        <Link to="/methodology">{text.home.aboutMethodology}</Link>
      </div>
      <p className="home-section-lead">{text.home.notEvaluatedLead}</p>
      <div className="home-check-grid">
        {text.home.notEvaluatedItems.map((item) => (
          <article key={item}>{item}</article>
        ))}
      </div>
    </section>
  );
}

function HomePrivacyNote() {
  return (
    <section className="home-privacy-panel">
      <MetricIcon type="shield" />
      <div>
        <h2>{text.home.privacyTitle}</h2>
        <p>{text.home.privacyText}</p>
      </div>
    </section>
  );
}

function HomeFinalCta() {
  return (
    <section className="home-final-cta">
      <div>
        <p className="eyebrow">{text.home.finalCtaEyebrow}</p>
        <h2>{text.home.finalCtaTitle}</h2>
      </div>
      <div className="hero-actions">
        <Link className="button-primary" to="/statements">{text.home.browseStatements}</Link>
        <a className="button-secondary" href="#home-rankings">{text.home.viewRankings}</a>
        <Link className="button-secondary" to="/methodology">{text.home.readMethodology}</Link>
      </div>
    </section>
  );
}

export function HomePage() {
  const { data, loading, error } = useAsync(getDashboard, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.home.emptyDashboard} />;

  return (
    <div className="home-page">
      <HomeHero data={data} />
      <HomeNavigationCards />
      <HomeRankings data={data} />
      <HomeLatestStatements statements={data.latest_statements} />
      <HomeCommitmentsSummary summary={data.active_government_program_summary} />
      <HomePurposePlaceholder />
      <HomeMethodologyPreview />
      <HomeNotEvaluatedPlaceholder />
      <HomePrivacyNote />
      <HomeFinalCta />
    </div>
  );
}
