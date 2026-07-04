import { Link } from "react-router-dom";

import type { PoliticalParty } from "../../types/politicalParty";

export function PartyCard({ party }: { party: PoliticalParty }) {
  return (
    <Link className="entity-card party-card" to={`/parties/${party.slug}`}>
      <article>
        <div className="entity-card-kicker">{party.short_name}</div>
        <h3>{party.full_name}</h3>
        {party.description ? <p>{party.description}</p> : null}
      </article>
    </Link>
  );
}
