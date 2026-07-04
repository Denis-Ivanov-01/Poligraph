import { getParties } from "../api/parties";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PartyList } from "../components/parties/PartyList";
import { useAsync } from "../utils/useAsync";

export function PartiesPage() {
  const { data, loading, error } = useAsync(getParties, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  return (
    <section className="section">
      <h1>{text.parties.title}</h1>
      {data?.length ? <PartyList parties={data} /> : <EmptyState message={text.parties.empty} />}
    </section>
  );
}
