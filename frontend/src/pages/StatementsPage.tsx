import { useState } from "react";

import { getStatements } from "../api/statements";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { LoadingState } from "../components/common/LoadingState";
import { StatementList } from "../components/statements/StatementList";
import { useAsync } from "../utils/useAsync";

export function StatementsPage() {
  const [query, setQuery] = useState("");
  const { data, loading, error } = useAsync(() => getStatements({ q: query || undefined }), [query]);
  return (
    <section className="section">
      <h1>{text.statements.title}</h1>
      <label className="search-field">
        {text.statements.searchLabel}
        <input value={query} onChange={(event) => setQuery(event.target.value)} />
      </label>
      {loading ? <LoadingState /> : null}
      {error ? <ErrorState message={error} /> : null}
      {!loading && !error ? data?.length ? <StatementList statements={data} /> : <EmptyState message={text.statements.empty} /> : null}
    </section>
  );
}
