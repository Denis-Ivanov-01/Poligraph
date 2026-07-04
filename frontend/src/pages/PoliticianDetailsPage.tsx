import { useParams } from "react-router-dom";

import { getPoliticianBySlug } from "../api/politicians";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { CriteriaAveragePanel } from "../components/statements/CriteriaAveragePanel";
import { PoliticianAvatar } from "../components/politicians/PoliticianAvatar";
import { StatementList } from "../components/statements/StatementList";
import { useAsync } from "../utils/useAsync";

export function PoliticianDetailsPage() {
  const { slug = "" } = useParams();
  const { data, loading, error } = useAsync(() => getPoliticianBySlug(slug), [slug]);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.politicians.notFound} />;
  return (
    <section className="section">
      <div className="profile-header">
        <PoliticianAvatar politician={data} />
        <div>
          <h1>{data.full_name}</h1>
          <p className="muted">{data.current_party?.full_name ?? text.politicians.noCurrentParty}</p>
        </div>
      </div>
      {data.biography ? <p>{data.biography}</p> : <EmptyState message={text.politicians.noBiography} />}
      <h2>{text.scores.averageScores}</h2>
      {data.average_scores ? (
        <CriteriaAveragePanel scores={data.average_scores} />
      ) : (
        <EmptyState message={text.politicians.noAnalyses} />
      )}
      <h2>{text.statements.title}</h2>
      {data.statements?.length ? <StatementList statements={data.statements} /> : <EmptyState message={text.statements.emptyForPolitician} />}
    </section>
  );
}
