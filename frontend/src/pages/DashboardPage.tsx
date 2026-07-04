import { getDashboard } from "../api/dashboard";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
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
      <h1>{text.dashboard.title}</h1>
      <div className="metrics">
        <div><span>{data.published_statement_count}</span><small>{text.home.publishedStatements}</small></div>
        <div><span>{data.party_count}</span><small>{text.home.parties}</small></div>
        <div><span>{data.politician_count}</span><small>{text.home.politicians}</small></div>
        <div className="metric-score"><ScoreBadge value={data.average_overall_score} size="large" /><small>{text.dashboard.averageOverall}</small></div>
      </div>
      <h2>{text.statements.latestPublished}</h2>
      {data.latest_statements.length ? <RankingTable statements={data.latest_statements} /> : <EmptyState message={text.home.noPublishedYet} />}
    </section>
  );
}
