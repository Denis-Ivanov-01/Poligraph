import { getPoliticians } from "../api/politicians";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { PoliticianList } from "../components/politicians/PoliticianList";
import { useAsync } from "../utils/useAsync";

export function PoliticiansPage() {
  const { data, loading, error } = useAsync(getPoliticians, []);
  if (loading) return <LoadingState />;
  if (error) return <ErrorState message={error} />;
  return (
    <section className="section">
      <h1>{text.politicians.title}</h1>
      {data?.length ? <PoliticianList politicians={data} /> : <EmptyState message={text.politicians.empty} />}
    </section>
  );
}
