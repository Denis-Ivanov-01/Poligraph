import { Link } from "react-router-dom";

import type { PoliticalParty } from "../../types/politicalParty";

export function PartyCard({ party }: { party: PoliticalParty }) {
  return (
    <article className="card">
      <h3>
        <Link to={`/parties/${party.slug}`}>{party.full_name}</Link>
      </h3>
      <p className="muted">{party.short_name}</p>
      {party.description ? <p>{party.description}</p> : null}
    </article>
  );
}
