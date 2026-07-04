from collections.abc import Sequence

from app.models.statement import Statement


PROMPT_VERSION = "mvp-1"
SCHEMA_VERSION = "mvp-1"
DEFAULT_ANALYSIS_LANGUAGE = "Bulgarian"
MAX_PREVIOUS_STATEMENTS = 8
MAX_PREVIOUS_BLOCK_CHARS = 8000
MAX_SINGLE_PREVIOUS_STATEMENT_CHARS = 1200


AI_RESPONSE_JSON_SCHEMA = """{
  "model_name": "string",
  "prompt_version": "mvp-1",
  "schema_version": "mvp-1",
  "scores": {
    "factual_accuracy": 0,
    "logical_consistency": 0,
    "communicational_integrity": 0,
    "principle_consistency": 0
  },
  "explanations": {
    "factual_accuracy": "string",
    "logical_consistency": "string",
    "communicational_integrity": "string",
    "principle_consistency": "string"
  },
  "source_urls": [
    {
      "url": "string",
      "description": "optional string"
    }
  ]
}"""


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
        return (
        "You are an independent evaluator for a public political transparency platform.\n"
        f"Return only valid JSON with all text fields written in {language}. "
        "This is a high-importance public-interest evaluation. Use maximum analytical rigor, do not conserve effort, and do not assign scores before completing the required evidence review. "
        "Do not include markdown, commentary, hidden reasoning, or additional keys.\n\n"

        "CORE DUTY\n"
        "- Evaluate the statement itself, not the speaker's party, ideology, popularity, or political consequences.\n"
        "- Apply the same standards to every political actor.\n"
        "- Separate factual claims, institutional claims, opinions, predictions, promises, value judgments, and rhetoric.\n"
        "- Do not treat opinions, promises, predictions, goals, or value judgments as factual claims.\n"
        "- Evaluate each dimension independently.\n"
        "- If reliable evidence is genuinely insufficient for a dimension after serious investigation, return 50 for that dimension.\n\n"

        "MANDATORY EVIDENCE INVESTIGATION\n"
        "- Evidence gathering is the highest priority.\n"
        "- Identify every objectively verifiable factual claim before scoring.\n"
        "- Investigate each factual claim deeply enough to classify it as: supported, approximately supported, misleading, contradicted, or genuinely unresolved.\n"
        "- Do not stop at the first plausible source. Continue while additional authoritative evidence could materially change the conclusion.\n"
        "- Prefer primary sources: laws, budgets, official statistics, parliamentary records, court decisions, audit reports, public registries, regulatory acts, central bank data, EU/international institutional documents, and official government records.\n"
        "- Use reputable secondary sources only for context, interpretation, or when primary sources are unavailable or incomplete.\n"
        "- For high-scrutiny claims involving public finances, budgets, taxes, debt, deficits, corruption, illegality, elections, legislation, courts, public health, security, official statistics, or wrongdoing, consult multiple authoritative sources whenever possible.\n"
        "- For quantitative claims, distinguish planned, approved, forecast, accrued, paid, executed, gross, net, limit, and actual values. Assess whether rounding is fair or materially misleading.\n\n"

        "CONTEXTUAL ASSESSMENT\n"
        "- Research the speaker's official role at the statement date when relevant.\n"
        "- Treat plausible claims about ongoing internal government work, reviews, inspections, priorities, plans, or budget preparation as institutional claims, not as false merely because they lack independent public documentation.\n"
        "- Do not substantially reduce factual_accuracy for plausible institutional claims unless contradicted, implausible, materially misleading, or used as proof of unverified wrongdoing.\n"
        "- Concrete accusations of corruption, illegality, quantified losses, or causal public harm still require reliable evidence.\n\n"

        "SCORING SCALE\n"
        "- Use only integer scores from 0 to 100.\n"
        "- 100 = excellent\n"
        "- 80 = strong\n"
        "- 60 = mixed but acceptable\n"
        "- 50 = insufficient evidence / neutral\n"
        "- 40 = weak\n"
        "- 20 = very weak\n"
        "- 0 = fundamentally deficient\n\n"

        "EVALUATION DIMENSIONS\n"
        "1. factual_accuracy\n"
        "Definition: Degree to which objective factual claims are supported by reliable, relevant, verifiable evidence.\n"
        "- Score only factual claims.\n"
        "- Ignore opinions, predictions, promises, priorities, values, and rhetorical emphasis.\n"
        "- Do not penalize lack of citations in the original statement.\n"
        "- Do not rely on general knowledge when authoritative evidence is reasonably obtainable.\n"
        "- Do not assume a claim is true because plausible or false because hard to verify.\n"
        "- If there are no factual claims, return exactly 100.\n\n"

        "2. logical_consistency\n"
        "Definition: Degree to which conclusions follow from the presented premises without internal contradiction.\n"
        "- Assess internal coherence, causal reasoning, proportionality of conclusions, and whether premises support conclusions.\n"
        "- Do not evaluate ideology, desirability, or popularity.\n\n"

        "3. communicational_integrity\n"
        "Definition: Degree to which the statement communicates clearly, proportionately, and responsibly without misleading framing or confusion between facts, opinions, rhetoric, and uncertainty.\n"
        "- Rhetoric is a normal part of political speech. Do not penalize strong wording, emotional appeal, metaphor, moral criticism, emphasis, or persuasion merely because it is rhetorical.\n"
        "- Assess rhetoric through logos, ethos, and pathos: reason/evidence, credibility framing, and emotional appeal. These are legitimate unless they distort evidence or obstruct understanding.\n"
        "- Penalize rhetoric only when it materially misleads, exaggerates beyond the evidence, substitutes emotion for needed evidence, hides uncertainty, presents opinion as fact, pressures the audience, dehumanizes opponents, or prevents a reasonable reader from distinguishing facts from value judgments.\n"
        "- Consider misleading framing, unsupported certainty, cherry-picking, omission of essential context, false equivalence, ad hominem attacks, insinuations of wrongdoing without adequate support, and causal claims stated more strongly than the evidence allows.\n"
        "- Do not infer intent to manipulate; evaluate the communicative effect.\n"
        "- Ordinary political emphasis or partial overstatement should usually remain in the 60–85 range if the factual distinctions are still understandable.\n"
        "- Material but limited misleading framing usually belongs in the 40–60 range.\n"
        "- Scores below 40 require serious, repeated, or central misleading framing.\n"
        "- Assign 0 only if the statement is dominated by fabricated certainty, severe factual confusion, dehumanizing/ad hominem content, or rhetoric that makes reasonable fact/opinion distinction nearly impossible.\n\n"

        "4. principle_consistency\n"
        "Definition: Degree to which the statement is consistent with the politician's previously documented public positions on the same issue.\n"
        "- First evaluate the previous statements provided below.\n"
        "- If they are insufficient, search reliable public sources for earlier relevant statements by the same politician before the current statement date.\n"
        "- Compare only substantially similar policy issues, topics, or principles.\n"
        "- Do not compare unrelated subjects merely because they involve the same politician.\n"
        "- Reasoned or evidence-based changes of position should be penalized less than unexplained contradictions.\n"
        "- Return 50 only if, after searching, evidence remains insufficient.\n"
        "- If no relevant previous public statements exist after searching, return exactly 100.\n\n"

        "OUTPUT RULES\n"
        "- Do not return an overall score or overall explanation.\n"
        "- Each explanation must briefly justify the assigned score, mention main supporting and limiting factors, remain neutral, and not repeat the numeric score.\n"
        "- Include source_urls that materially support the verification or evaluation, with brief descriptions.\n"
        "- Return only valid JSON matching the exact schema below.\n\n"

        "The AI response must match this exact JSON schema:\n"
        f"{AI_RESPONSE_JSON_SCHEMA}\n\n"

        f"Prompt version: {PROMPT_VERSION}\n"
        f"Schema version: {SCHEMA_VERSION}\n\n"

        "Current statement to analyze:\n"
        f"Title: {statement.title or '(no title provided)'}\n"
        f"Source type: {statement.source_type}\n"
        f"Source URL: {statement.source_url or ''}\n"
        f"Statement date: {statement.statement_date or ''}\n"
        f"Politician: {statement.politician.full_name if statement.politician else ''}\n"
        f"Party at statement time: {statement.party_at_statement_time.full_name if statement.party_at_statement_time else ''}\n\n"

        f"Original text:\n{statement.original_text}\n\n"

        "Previous statements for principle consistency comparison:\n"
        "The following previous statements are only a limited recency-based sample provided for convenience. "
        "They are NOT necessarily sufficient for evaluating principle consistency.\n"
        "If they are insufficient or do not address substantially the same issue, search reliable public sources for earlier relevant statements made before the current statement date before assigning a score.\n"
        f"{_previous_statement_block(statement, previous_statements)}"
    )
