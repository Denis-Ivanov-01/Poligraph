import { Link } from "react-router-dom";

import { getDashboard } from "../api/dashboard";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { MetricIcon } from "../components/common/MetricIcon";
import { ScoreBadge } from "../components/common/ScoreBadge";
import { RankingTable } from "../components/dashboard/RankingTable";
import { useAsync } from "../utils/useAsync";

export function DashboardPage() {
  const { data, loading, error } = useAsync(getDashboard, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.dashboard.unavailable} />;
  return (
    <section className="section">
      <div className="page-hero">
        <div className="hero-copy">
          <p className="eyebrow">{text.home.eyebrow}</p>
          <h1>{text.home.heading}</h1>
          <p className="hero-subtitle">{text.home.subtitle}</p>
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
          <small>{text.dashboard.averageOverall}</small>
        </div>
      </div>
      <div className="section-heading">
        <h2>{text.statements.latestPublished}</h2>
        <Link to="/statements">{text.statements.browseAll}</Link>
      </div>
      {data.latest_statements.length ? <RankingTable statements={data.latest_statements} /> : <EmptyState message={text.home.noPublishedYet} />}
    </section>
  );
}
