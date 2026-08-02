from app.models.statement import Statement
from app.resources import resource_text
from app.services.statements_prompt_template import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    STATEMENT_ANALYSIS_PROMPT_TEMPLATE,
    build_ai_response_json_schema,
)


DEFAULT_ANALYSIS_LANGUAGE = resource_text("language")


def build_statement_prompt(
    statement: Statement,
    language: str = DEFAULT_ANALYSIS_LANGUAGE,
) -> str:
    return STATEMENT_ANALYSIS_PROMPT_TEMPLATE.format(
        language=language,
        response_json_schema=build_ai_response_json_schema(),
        prompt_version=PROMPT_VERSION,
        schema_version=SCHEMA_VERSION,
        title=statement.title or "(no title provided)",
        source_type=statement.source_type,
        source_url=statement.source_url or "",
        statement_date=statement.statement_date or "",
        politician=statement.politician.full_name if statement.politician else "",
        party_at_statement_time=statement.party_at_statement_time.full_name if statement.party_at_statement_time else "",
        original_text=statement.original_text,
    )
