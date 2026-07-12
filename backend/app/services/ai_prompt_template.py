import json

from app.models.ai_analysis import AiRun, StatementAiAnalysis
from app.models.evidence import EvidenceItem
from app.models.statement_claim import StatementClaim
from app.schemas.ai_analysis import (
    STATEMENT_CHECKABILITY_VALUES,
    STATEMENT_CLAIM_TYPES,
    STATEMENT_CONFIDENCE_LEVELS,
    STATEMENT_DIMENSIONS,
    STATEMENT_EVIDENCE_REVIEW_COMPLETENESS_VALUES,
    STATEMENT_FACTUAL_ACCURACY_APPLICABILITIES,
    STATEMENT_MATERIALITY_VALUES,
    STATEMENT_VERIFICATION_STATUSES,
)
from app.services.commitment_service import EVIDENCE_SOURCE_TYPES
from app.services.prompt_schema_builder import db_fields_contract, enum_list_contract


PROMPT_VERSION = "mvp-3"
SCHEMA_VERSION = "mvp-3"
MAX_PREVIOUS_STATEMENTS = 8
MAX_PREVIOUS_BLOCK_CHARS = 8000
MAX_SINGLE_PREVIOUS_STATEMENT_CHARS = 1200


def build_ai_response_json_schema() -> str:
    run_fields = db_fields_contract(
        AiRun,
        ["model_name", "prompt_version", "schema_version"],
        nullable_overrides={"model_name": False, "prompt_version": False, "schema_version": False},
    )
    statement_fields = db_fields_contract(
        StatementAiAnalysis,
        ["factual_accuracy_applicability", "evidence_review_completeness", "human_review_recommended", "human_review_reason"],
        enum_fields={
            "factual_accuracy_applicability": STATEMENT_FACTUAL_ACCURACY_APPLICABILITIES,
            "evidence_review_completeness": STATEMENT_EVIDENCE_REVIEW_COMPLETENESS_VALUES,
        },
        nullable_overrides={
            "factual_accuracy_applicability": False,
            "evidence_review_completeness": False,
            "human_review_recommended": False,
        },
    )
    claim_fields = db_fields_contract(
        StatementClaim,
        [
            "exact_quote",
            "normalized_claim",
            "claim_type",
            "checkability",
            "materiality",
            "materiality_reason",
            "ai_verification_status",
            "confidence_level",
            "evidence_summary",
            "missing_or_uncertain_evidence",
        ],
        enum_fields={
            "claim_type": STATEMENT_CLAIM_TYPES,
            "checkability": STATEMENT_CHECKABILITY_VALUES,
            "materiality": STATEMENT_MATERIALITY_VALUES,
            "ai_verification_status": STATEMENT_VERIFICATION_STATUSES,
            "confidence_level": STATEMENT_CONFIDENCE_LEVELS,
        },
        nullable_overrides={
            "claim_type": False,
            "checkability": False,
            "materiality": False,
            "ai_verification_status": False,
            "confidence_level": False,
        },
    )
    source_fields = db_fields_contract(
        EvidenceItem,
        [
            "title",
            "url",
            "source_type",
            "publisher",
            "published_at",
            "quote_or_relevant_excerpt",
            "description",
            "reliability_level",
        ],
        enum_fields={"source_type": EVIDENCE_SOURCE_TYPES, "reliability_level": STATEMENT_CONFIDENCE_LEVELS},
        nullable_overrides={"source_type": False, "reliability_level": False},
    )
    return json.dumps(
        {
            "model_name": run_fields["model_name"],
            "prompt_version": PROMPT_VERSION,
            "schema_version": SCHEMA_VERSION,
            "statement_analysis": {
                "factual_accuracy_applicability": statement_fields["factual_accuracy_applicability"],
                "scores": {
                    "factual_accuracy": 80,
                    "logical_consistency": 75,
                    "communicational_integrity": 70,
                    "principle_consistency": 100,
                },
                "explanations": {
                    "factual_accuracy": "string",
                    "logical_consistency": "string",
                    "communicational_integrity": "string",
                    "principle_consistency": "string",
                },
                "evidence_review_completeness": statement_fields["evidence_review_completeness"],
                "human_review_recommended": statement_fields["human_review_recommended"],
                "human_review_reason": statement_fields["human_review_reason"],
            },
            "claims": [
                {
                    "claim_ref": "C1",
                    **claim_fields,
                    "used_for_dimensions": enum_list_contract(STATEMENT_DIMENSIONS),
                    "source_refs": ["S1"],
                }
            ],
            "sources": [
                {
                    "source_ref": "S1",
                    **source_fields,
                }
            ],
        },
        indent=2,
        ensure_ascii=False,
    )
STATEMENT_ANALYSIS_PROMPT_TEMPLATE = """You are an independent evaluator for a public political transparency platform.
Return only valid JSON with all text fields written in {language}. This is a high-importance public-interest evaluation. Use maximum analytical rigor, do not conserve effort, and do not assign scores before completing the required evidence review. Do not include markdown, commentary, hidden reasoning, or additional keys.

CORE DUTY
- Evaluate the statement itself, not the speaker's party, ideology, popularity, or political consequences.
- Apply the same standards to every political actor.
- Separate factual claims, institutional claims, opinions, predictions, promises, value judgments, and rhetoric.
- Do not treat opinions, promises, predictions, goals, or value judgments as factual claims.
- Evaluate each dimension independently.
- If reliable evidence is genuinely insufficient for a dimension after serious investigation, return 50 for that dimension.
- Return extracted claims and sources in normalized form. Claim/source refs such as C1 and S1 are temporary local JSON refs only.

MANDATORY EVIDENCE INVESTIGATION
- Evidence gathering is the highest priority.
- Identify every objectively verifiable factual claim before scoring.
- Investigate each factual claim deeply enough to classify it as: supported, approximately supported, misleading, contradicted, or genuinely unresolved.
- Do not stop at the first plausible source. Continue while additional authoritative evidence could materially change the conclusion.
- Prefer primary sources: laws, budgets, official statistics, parliamentary records, court decisions, audit reports, public registries, regulatory acts, central bank data, EU/international institutional documents, and official government records.
- Use reputable secondary sources only for context, interpretation, or when primary sources are unavailable or incomplete.
- For high-scrutiny claims involving public finances, budgets, taxes, debt, deficits, corruption, illegality, elections, legislation, courts, public health, security, official statistics, or wrongdoing, consult multiple authoritative sources whenever possible.
- For quantitative claims, distinguish planned, approved, forecast, accrued, paid, executed, gross, net, limit, and actual values. Assess whether rounding is fair or materially misleading.

CONTEXTUAL ASSESSMENT
- Research the speaker's official role at the statement date when relevant.
- Treat plausible claims about ongoing internal government work, reviews, inspections, priorities, plans, or budget preparation as institutional claims, not as false merely because they lack independent public documentation.
- Do not substantially reduce factual_accuracy for plausible institutional claims unless contradicted, implausible, materially misleading, or used as proof of unverified wrongdoing.
- Concrete accusations of corruption, illegality, quantified losses, or causal public harm still require reliable evidence.

SCORING SCALE
- Use only integer scores from 0 to 100.
- 100 = excellent
- 80 = strong
- 60 = mixed but acceptable
- 50 = insufficient evidence / neutral
- 40 = weak
- 20 = very weak
- 0 = fundamentally deficient

EVALUATION DIMENSIONS
1. factual_accuracy
Definition: Degree to which objective factual claims are supported by reliable, relevant, verifiable evidence.
- Score only factual claims.
- Ignore opinions, predictions, promises, priorities, values, and rhetorical emphasis.
- Do not penalize lack of citations in the original statement.
- Do not rely on general knowledge when authoritative evidence is reasonably obtainable.
- Do not assume a claim is true because plausible or false because hard to verify.
- If there are no factual claims, return exactly 100.

2. logical_consistency
Definition: Degree to which conclusions follow from the presented premises without internal contradiction.
- Assess internal coherence, causal reasoning, proportionality of conclusions, and whether premises support conclusions.
- Do not evaluate ideology, desirability, or popularity.

3. communicational_integrity
Definition: Degree to which the statement communicates clearly, proportionately, and responsibly without misleading framing or confusion between facts, opinions, rhetoric, and uncertainty.
- Rhetoric is a normal part of political speech. Do not penalize strong wording, emotional appeal, metaphor, moral criticism, emphasis, or persuasion merely because it is rhetorical.
- Assess rhetoric through logos, ethos, and pathos: reason/evidence, credibility framing, and emotional appeal. These are legitimate unless they distort evidence or obstruct understanding.
- Penalize rhetoric only when it materially misleads, exaggerates beyond the evidence, substitutes emotion for needed evidence, hides uncertainty, presents opinion as fact, pressures the audience, dehumanizes opponents, or prevents a reasonable reader from distinguishing facts from value judgments.
- Consider misleading framing, unsupported certainty, cherry-picking, omission of essential context, false equivalence, ad hominem attacks, insinuations of wrongdoing without adequate support, and causal claims stated more strongly than the evidence allows.
- Do not infer intent to manipulate; evaluate the communicative effect.
- Ordinary political emphasis or partial overstatement should usually remain in the 60-85 range if the factual distinctions are still understandable.
- Material but limited misleading framing usually belongs in the 40-60 range.
- Scores below 40 require serious, repeated, or central misleading framing.
- Assign 0 only if the statement is dominated by fabricated certainty, severe factual confusion, dehumanizing/ad hominem content, or rhetoric that makes reasonable fact/opinion distinction nearly impossible.

4. principle_consistency
Definition: Degree to which the statement is consistent with the politician's previously documented public positions on the same issue.
- First evaluate the previous statements provided below.
- If they are insufficient, search reliable public sources for earlier relevant statements by the same politician before the current statement date.
- Compare only substantially similar policy issues, topics, or principles.
- Do not compare unrelated subjects merely because they involve the same politician.
- Reasoned or evidence-based changes of position should be penalized less than unexplained contradictions.
- Return 50 only if, after searching, evidence remains insufficient.
- If no relevant previous public statements exist after searching, return exactly 100.

OUTPUT RULES
- Do not return an overall score or overall explanation.
- Put the four dimension scores inside statement_analysis.scores.
- Each explanation must briefly justify the assigned score, mention main supporting and limiting factors, remain neutral, and not repeat the numeric score.
- Include sources that materially support the verification or evaluation, with source_ref values used by claims.source_refs.
- For factual_accuracy, set factual_accuracy_applicability to "not_applicable" only when the statement contains no factual claims.
- Use evidence_review_completeness: "complete", "partial", or "limited_by_public_evidence".
- Set human_review_recommended and human_review_reason when the output should receive human factual review.
- Use only enum values shown in the schema. Do not add fields outside the schema.
- Return only valid JSON matching the exact schema below.

The AI response must match this exact JSON schema:
{response_json_schema}

Prompt version: {prompt_version}
Schema version: {schema_version}

Current statement to analyze:
Title: {title}
Source type: {source_type}
Source URL: {source_url}
Statement date: {statement_date}
Politician: {politician}
Party at statement time: {party_at_statement_time}

Original text:
{original_text}

Previous statements for principle consistency comparison:
The following previous statements are only a limited recency-based sample provided for convenience. They are NOT necessarily sufficient for evaluating principle consistency.
If they are insufficient or do not address substantially the same issue, search reliable public sources for earlier relevant statements made before the current statement date before assigning a score.
{previous_statements}
"""
