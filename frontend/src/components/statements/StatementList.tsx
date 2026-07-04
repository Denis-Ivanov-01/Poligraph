import type { StatementListItem } from "../../types/statement";
import { StatementCard } from "./StatementCard";

export function StatementList({ statements }: { statements: StatementListItem[] }) {
  return (
    <div className="list">
      {statements.map((statement) => (
        <StatementCard key={statement.id} statement={statement} />
      ))}
    </div>
  );
}
