import { Link } from "react-router-dom";

import { getDashboard } from "../api/dashboard";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { ScoreBadge } from "../components/common/ScoreBadge";
import { RankingTable } from "../components/dashboard/RankingTable";
import { useAsync } from "../utils/useAsync";

function MetricIcon({ type }: { type: "statements" | "politicians" | "parties" | "score" }) {
  const icons = {
    statements: (
      <>
        <path d="M8 5.5h8" />
        <path d="M8 10h8" />
        <path d="M8 14.5h5" />
        <path d="M5 2.75h14v18.5H5z" />
      </>
    ),
    politicians: (
      <>
        <path d="M8.5 9a3.5 3.5 0 1 0 7 0 3.5 3.5 0 0 0-7 0z" />
        <path d="M5 20c1.2-3.2 3.5-5 7-5s5.8 1.8 7 5" />
      </>
    ),
    parties: (
      <>
        <path d="M4.5 20h15" />
        <path d="M6 17V9l6-4 6 4v8" />
        <path d="M9 17v-5h6v5" />
      </>
    ),
    score: (
      <>
        <path d="M12 3.5l2.4 5 5.5.8-4 3.9.9 5.5L12 16.1l-4.8 2.6.9-5.5-4-3.9 5.5-.8z" />
      </>
    )
  };

  return (
    <svg className="metric-icon" viewBox="0 0 24 24" aria-hidden="true">
      <g fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
        {icons[type]}
      </g>
    </svg>
  );
}

export function HomePage() {
  const { data, loading, error } = useAsync(getDashboard, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.home.emptyDashboard} />;

  return (
    <section className="section">
      <div className="page-hero">
        <div className="hero-copy">
          <p className="eyebrow">{text.home.eyebrow}</p>
          <h1>{text.home.heading}</h1>
          <p className="hero-subtitle">
            {text.home.subtitle}
          </p>
          <div className="hero-actions">
            <Link className="button-primary" to="/statements">{text.home.browseStatements}</Link>
            <Link className="button-secondary" to="/politicians">{text.home.browsePoliticians}</Link>
            <Link className="button-secondary" to="/parties">{text.home.browseParties}</Link>
          </div>
        </div>
        <div className="trust-badges" aria-label={text.home.trustBadgesAria}>
          <span>{text.home.aiPoweredAnalysis}</span>
          <span>{text.home.transparentMethodology}</span>
          <span>{text.home.evidenceBasedEvaluation}</span>
        </div>
      </div>
      <div className="metrics">
        <div>
          <MetricIcon type="statements" />
          <span>{data.published_statement_count}</span>
          <small>{text.home.publishedStatements}</small>
        </div>
        <div>
          <MetricIcon type="politicians" />
          <span>{data.politician_count}</span>
          <small>{text.home.politicians}</small>
        </div>
        <div>
          <MetricIcon type="parties" />
          <span>{data.party_count}</span>
          <small>{text.home.parties}</small>
        </div>
        <div className="metric-score">
          <MetricIcon type="score" />
          <ScoreBadge value={data.average_overall_score} size="large" />
          <small>{text.home.averageOverallScore}</small>
        </div>
      </div>
      <div className="section-heading">
        <h2>{text.statements.latest}</h2>
        <Link to="/statements">{text.statements.browseAll}</Link>
      </div>
      {data.latest_statements.length ? <RankingTable statements={data.latest_statements} /> : <EmptyState message={text.home.noPublishedYet} />}
    </section>
  );
}
