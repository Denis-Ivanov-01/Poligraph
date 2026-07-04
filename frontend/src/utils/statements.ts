import type { StatementListItem } from "../types/statement";
import { text } from "../i18n/resources";

export function statementDisplayTitle(statement: Pick<StatementListItem, "title" | "statement_date" | "source_type">) {
  return statement.title?.trim() || `${text.statements.untitledPrefix} ${statement.statement_date ?? statement.source_type}`;
}
