import { useParams } from "react-router-dom";

import { getPartyBySlug } from "../api/parties";
import { formatResource, text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PoliticianList } from "../components/politicians/PoliticianList";
import { CriteriaAveragePanel } from "../components/statements/CriteriaAveragePanel";
import { StatementList } from "../components/statements/StatementList";
import { useAsync } from "../utils/useAsync";

export function PartyDetailsPage() {
  const { slug = "" } = useParams();
  const { data, loading, error } = useAsync(() => getPartyBySlug(slug), [slug]);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  if (!data) return <EmptyState message={text.parties.notFound} />;
  const members = data.members ?? [];
  return (
    <section className="section">
      <h1>{data.full_name}</h1>
      <p className="muted">{data.short_name}</p>
      {data.description ? <p>{data.description}</p> : <EmptyState message={text.parties.noDescription} />}
      <h2>{text.scores.averageScores}</h2>
      {data.average_scores ? (
        <CriteriaAveragePanel scores={data.average_scores} />
      ) : (
        <EmptyState message={text.parties.noAnalyses} />
      )}
      <h2>{text.parties.members}</h2>
      {members.length ? (
        <>
          <PoliticianList politicians={members.map((member) => member.politician)} />
          <div className="membership-list">
            {members.map((member) => (
              <p className="muted" key={member.id}>
                {member.politician.full_name}: {member.end_date ? text.parties.formerMember : text.parties.currentMember} {text.common.separator}{" "}
                {formatResource(text.parties.membershipDates, {
                  start: member.start_date ?? text.parties.unknownStart,
                  end: member.end_date ?? text.parties.present
                })}
              </p>
            ))}
          </div>
        </>
      ) : (
        <EmptyState message={text.parties.noMembers} />
      )}
      <h2>{text.statements.title}</h2>
      {data.statements?.length ? <StatementList statements={data.statements} /> : <EmptyState message={text.statements.emptyForParty} />}
    </section>
  );
}
