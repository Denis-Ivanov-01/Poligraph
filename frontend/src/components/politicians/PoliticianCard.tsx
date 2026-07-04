import { Link } from "react-router-dom";

import { text } from "../../i18n/resources";
import type { Politician } from "../../types/politician";
import { PoliticianAvatar } from "./PoliticianAvatar";

export function PoliticianCard({ politician }: { politician: Politician }) {
  return (
    <article className="card politician-card">
      <PoliticianAvatar politician={politician} className="profile-photo-small" />
      <div>
        <h3>
          <Link to={`/politicians/${politician.slug}`}>{politician.full_name}</Link>
        </h3>
        <p className="muted">{politician.current_party?.short_name ?? text.politicians.noCurrentParty}</p>
        {politician.biography ? <p>{politician.biography}</p> : null}
      </div>
    </article>
  );
}
