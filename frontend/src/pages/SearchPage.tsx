import { FormEvent, useState } from "react";

import { search, type SearchResults } from "../api/search";
import { text } from "../i18n/resources";
import { EmptyState } from "../components/common/EmptyState";
import { ErrorState } from "../components/common/ErrorState";
import { PartyList } from "../components/parties/PartyList";
import { PoliticianList } from "../components/politicians/PoliticianList";
import { StatementList } from "../components/statements/StatementList";

export function SearchPage() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    setError(null);
    try {
      setResults(await search(query.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : text.search.failed);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="section">
      <h1>{text.search.title}</h1>
      <form onSubmit={onSubmit} className="search-row">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={text.search.placeholder} />
        <button type="submit">{text.search.button}</button>
      </form>
      {loading ? <p className="muted">{text.search.loading}</p> : null}
      {error ? <ErrorState message={error} /> : null}
      {results ? (
        <div className="search-results">
          <h2>{text.parties.title}</h2>
          {results.parties.length ? <PartyList parties={results.parties} /> : <EmptyState message={text.search.noParties} />}
          <h2>{text.politicians.title}</h2>
          {results.politicians.length ? <PoliticianList politicians={results.politicians} /> : <EmptyState message={text.search.noPoliticians} />}
          <h2>{text.statements.title}</h2>
          {results.statements.length ? <StatementList statements={results.statements} /> : <EmptyState message={text.search.noStatements} />}
        </div>
      ) : null}
    </section>
  );
}
