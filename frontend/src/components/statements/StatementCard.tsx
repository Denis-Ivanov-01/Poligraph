import { Link } from "react-router-dom";

import { text } from "../../i18n/resources";
import type { StatementListItem } from "../../types/statement";
import { statementDisplayTitle } from "../../utils/statements";
import { ScoreBadge } from "../common/ScoreBadge";

export function StatementCard({ statement }: { statement: StatementListItem }) {
  return (
    <Link className="statement-tile" to={`/statements/${statement.id}`}>
      <article>
        <div className="statement-tile-main">
          <h3>{statementDisplayTitle(statement)}</h3>
          <p className="muted">
            {statement.politician.full_name}
            {statement.party_at_statement_time ? `, ${statement.party_at_statement_time.short_name}` : ""}
          </p>
          <p className="statement-meta">
            {statement.statement_date ?? text.common.noDate} {text.common.separator} {statement.source_type}
          </p>
        </div>
        <div className="statement-tile-score">
          <span>{text.scores.overall}</span>
          <ScoreBadge value={statement.overall_score} size="large" />
        </div>
      </article>
    </Link>
  );
}
