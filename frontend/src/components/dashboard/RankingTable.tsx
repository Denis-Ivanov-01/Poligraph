import { Link } from "react-router-dom";

import { text } from "../../i18n/resources";
import type { StatementListItem } from "../../types/statement";
import { statementDisplayTitle } from "../../utils/statements";
import { ScoreBadge } from "../common/ScoreBadge";

export function RankingTable({ statements }: { statements: StatementListItem[] }) {
  return (
    <div className="ranking-list">
      {statements.map((statement) => (
        <Link className="ranking-row" to={`/statements/${statement.id}`} key={statement.id}>
          <div className="ranking-row-content">
            <span className="ranking-kicker">
              {statement.statement_date ?? text.common.noDate} {text.common.separator} {statement.source_type}
            </span>
            <strong>{statementDisplayTitle(statement)}</strong>
            <span className="ranking-politician">
              {statement.politician.full_name}
              {statement.party_at_statement_time ? `, ${statement.party_at_statement_time.short_name}` : ""}
            </span>
          </div>
          <div className="ranking-score">
            <span>{text.scores.overall}</span>
            <ScoreBadge value={statement.overall_score} size="medium" />
          </div>
        </Link>
      ))}
    </div>
  );
}
