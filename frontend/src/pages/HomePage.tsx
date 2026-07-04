import { Link } from "react-router-dom";

import { getDashboard } from "../api/dashboard";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { ScoreBadge } from "../components/common/ScoreBadge";
import { RankingTable } from "../components/dashboard/RankingTable";
import { useAsync } from "../utils/useAsync";

export function HomePage() {
  const { data, loading, error } = useAsync(getDashboard, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.home.emptyDashboard} />;

  return (
    <section className="section">
      <div className="page-hero">
        <p className="eyebrow">{text.home.eyebrow}</p>
        <h1>{text.home.heading}</h1>
      </div>
      <div className="metrics">
        <div><span>{data.published_statement_count}</span><small>{text.home.publishedStatements}</small></div>
        <div><span>{data.politician_count}</span><small>{text.home.politicians}</small></div>
        <div><span>{data.party_count}</span><small>{text.home.parties}</small></div>
        <div className="metric-score"><ScoreBadge value={data.average_overall_score} size="large" /><small>{text.home.averageOverallScore}</small></div>
      </div>
      <h2>{text.statements.latest}</h2>
      {data.latest_statements.length ? <RankingTable statements={data.latest_statements} /> : <EmptyState message={text.home.noPublishedYet} />}
      <p><Link to="/statements">{text.statements.browseAll}</Link></p>
    </section>
  );
}
