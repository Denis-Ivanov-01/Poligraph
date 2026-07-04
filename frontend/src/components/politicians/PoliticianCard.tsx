import { Link } from "react-router-dom";

import { text } from "../../i18n/resources";
import type { Politician } from "../../types/politician";
import { PoliticianAvatar } from "./PoliticianAvatar";

export function PoliticianCard({ politician }: { politician: Politician }) {
  return (
    <Link className="entity-card politician-card" to={`/politicians/${politician.slug}`}>
      <article>
        <PoliticianAvatar politician={politician} className="profile-photo-small" />
        <div>
          <div className="entity-card-kicker">
            {politician.current_party?.short_name ?? text.politicians.noCurrentParty}
          </div>
          <h3>{politician.full_name}</h3>
          {politician.biography ? <p>{politician.biography}</p> : null}
        </div>
      </article>
    </Link>
  );
}
