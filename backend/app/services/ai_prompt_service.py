from collections.abc import Sequence

from app.models.statement import Statement
from app.resources import resource_text
from app.services.ai_prompt_template import (
    AI_RESPONSE_JSON_SCHEMA,
    MAX_PREVIOUS_BLOCK_CHARS,
    MAX_PREVIOUS_STATEMENTS,
    MAX_SINGLE_PREVIOUS_STATEMENT_CHARS,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STATEMENT_ANALYSIS_PROMPT_TEMPLATE,
)


DEFAULT_ANALYSIS_LANGUAGE = resource_text("language")


def _truncate_text(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[: max_chars - 15].rstrip() + "\n   [truncated]"


def _previous_statement_block(current_statement: Statement, previous_statements: Sequence[Statement]) -> str:
    if not current_statement.politician_id or not current_statement.statement_date:
        return "No previous statements are available for consistency comparison."

    eligible = [
        previous
        for previous in previous_statements
        if previous.id != current_statement.id
        and previous.politician_id == current_statement.politician_id
        and previous.statement_date
        and previous.statement_date < current_statement.statement_date
    ]
    eligible.sort(key=lambda previous: previous.statement_date, reverse=True)

    if not eligible:
        return "No previous statements are available for consistency comparison."

    rows = []
    block_chars = 0
    for previous in eligible:
        if len(rows) >= MAX_PREVIOUS_STATEMENTS:
            break
        analysis = previous.ai_analysis
        score = analysis.principle_consistency_score if analysis and analysis.is_published else "not analyzed"
        party = previous.party_at_statement_time.short_name if previous.party_at_statement_time else "no party recorded"
        politician = previous.politician.full_name if previous.politician else "unknown politician"
        row = "\n".join(
            [
                f"{len(rows) + 1}. Title: {previous.title or '(no title provided)'}",
                f"   Politician: {politician}",
                f"   Party at statement time: {party}",
                f"   Date: {previous.statement_date}",
                f"   Existing principle consistency score: {score}",
                f"   Text: {_truncate_text(previous.original_text, MAX_SINGLE_PREVIOUS_STATEMENT_CHARS)}",
            ]
        )
        separator_chars = 2 if rows else 0
        if block_chars + separator_chars + len(row) > MAX_PREVIOUS_BLOCK_CHARS:
            break
        rows.append(row)
        block_chars += separator_chars + len(row)

    if not rows:
        return "No previous statements fit within the configured consistency comparison limits."
    return "\n\n".join(rows)


def build_statement_prompt(
    statement: Statement,
    previous_statements: Sequence[Statement] = (),
    language: str = DEFAULT_ANALYSIS_LANGUAGE,
) -> str:
    return STATEMENT_ANALYSIS_PROMPT_TEMPLATE.format(
        language=language,
        response_json_schema=AI_RESPONSE_JSON_SCHEMA,
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        title=statement.title or "(no title provided)",
        source_type=statement.source_type,
        source_url=statement.source_url or "",
        statement_date=statement.statement_date or "",
        politician=statement.politician.full_name if statement.politician else "",
        party_at_statement_time=statement.party_at_statement_time.full_name if statement.party_at_statement_time else "",
        original_text=statement.original_text,
        previous_statements=_previous_statement_block(statement, previous_statements),
    )
