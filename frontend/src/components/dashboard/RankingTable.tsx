import { Link } from "react-router-dom";

import type { StatementListItem } from "../../types/statement";
import { statementDisplayTitle } from "../../utils/statements";
import { ScoreBadge } from "../common/ScoreBadge";

export function RankingTable({ statements }: { statements: StatementListItem[] }) {
  return (
    <div className="ranking-list">
      {statements.map((statement) => (
        <Link className="ranking-row" to={`/statements/${statement.id}`} key={statement.id}>
          <div>
            <strong>{statementDisplayTitle(statement)}</strong>
            <span>{statement.politician.full_name}</span>
          </div>
          <ScoreBadge value={statement.overall_score} size="medium" />
        </Link>
      ))}
    </div>
  );
}
