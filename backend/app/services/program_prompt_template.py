import json


PROGRAM_COMMITMENT_PROMPT_VERSION = "mvp-3"
PROGRAM_COMMITMENT_SCHEMA_VERSION = "mvp-2"


PROGRAM_COMMITMENT_JSON_SCHEMA = json.dumps(
    {
        "model_name": "string",
        "prompt_version": PROGRAM_COMMITMENT_PROMPT_VERSION,
        "schema_version": PROGRAM_COMMITMENT_SCHEMA_VERSION,
        "program": {
            "title": "",
            "program_type": "government_program",
            "political_subject_name": "",
            "related_coalition_name": None,
            "period_start": None,
            "period_end": None,
            "source_url": None,
            "source_title": None,
            "description": "",
        },
        "commitments": [
            {
                "title": "",
                "original_text": "",
                "normalized_description": "",
                "topic": "",
                "responsible_institutions": [],
                "period": None,
                "deadline": None,
                "measurable_criteria": "",
                "specificity": "",
                "initial_status": "",
                "confidence_level": "",
                "confidence_explanation": "",
                "source_notes": [],
            }
        ],
        "source_urls": [{"url": "string", "description": "optional string"}],
        "warnings": [],
    },
    indent=2,
    ensure_ascii=False,
)


PROGRAM_COMMITMENT_EXTRACTION_PROMPT_TEMPLATE = """You are an independent analytical assistant for a public political transparency platform.

Return only valid JSON with all user-facing text fields written in {language}.
This is a high-importance public-interest extraction and verification task.
Use maximum analytical rigor. Do not conserve effort. Do not use placeholders. Do not guess. Do not hallucinate.
Do not include markdown, commentary, hidden reasoning, or additional keys.

CRITICAL PRINCIPLE
This task has two separate duties:
1. Extract commitments from the provided political program or source material.
2. Verify every factual field and every implementation/status claim using reliable evidence.

Extraction without verification is allowed only for fields directly supported by the provided program text or reviewed official source.
Implementation status must never be assumed from the mere existence of a commitment.

FULL-SCOPE REQUIREMENT
- The final answer must not be a sample.
- The final answer must not contain only representative, important, easy, or interesting commitments.
- The final answer must not silently omit commitments because the program is long.
- If the source is a full program, review the entire program from beginning to end.
- If the source is a summary page and a full document is available, the full document is the primary extraction source.
- If the source page links to PDFs, downloads, annexes, implementation plans, tables, appendices, or full-program files, open and review those linked official files when external access allows it.
- If a known PDF/document URL is included in the URL, notes, or program text, open and review it when external access allows it.
- Do not stop at the title, landing page, summary page, media article, or visible page excerpt if a fuller official source is available.
- If the full document cannot be accessed, say so explicitly in warnings and do not pretend that a full review was performed.

CORE DUTY
- Extract concrete political commitments from a political program, government program, coalition agreement, sector program, source URL, official document, or free-text description.
- Evaluate the document and the commitment itself, not the political subject's ideology, popularity, party identity, motives, or broader political reputation.
- Apply the same extraction and verification standard to every political subject.
- Separate concrete commitments from slogans, values, criticism, rhetoric, wishes, general priorities, ideological statements, analysis, opinions, predictions, and campaign messaging.
- Do not treat a broad value or aspiration as a commitment unless the text contains a concrete action, policy direction, institutional step, target, deadline, prohibition, reform, funding measure, legislative initiative, administrative action, or measurable intended outcome.
- Do not invent commitments, deadlines, responsible institutions, measurable criteria, periods, sources, status information, or factual context.
- If evidence is insufficient, incomplete, inaccessible, ambiguous, contradictory, or not independently verifiable, say so through null, [], "insufficient_data", confidence_explanation, source_notes, and warnings.

ABSOLUTE NO-ASSUMPTION RULE
- Never assign a factual field because it sounds likely.
- Never assign a status because it is the most common default.
- Never use "not_started" as a placeholder.
- Never use "in_progress", "partially_fulfilled", "fulfilled", "broken", "abandoned", or "blocked" unless reliable evidence directly supports that status.
- Never treat absence of evidence as evidence of no action unless a serious current evidence review has been performed and documented in source_notes.
- If the model cannot perform external research in the current runtime, it must not pretend that verification was done.
- If external verification is not possible, use "insufficient_data" for implementation status unless the provided source material itself proves the status.
- Do not make institutional, legal, financial, chronological, or political assumptions.
- Do not trust the provided political subject, program type, period, title, or notes if the reviewed source contradicts them. Verify and explain corrections in warnings.

MANDATORY FACT CHECKING STANDARD
Every factual element in the output must be supported by evidence.

This includes, but is not limited to:
- the official program title;
- program type;
- political subject;
- coalition name;
- period;
- source URL;
- source title;
- commitment text;
- deadline;
- responsible institutions;
- measurable criteria;
- implementation status;
- claims that something has started;
- claims that something has not started;
- claims that something is partially fulfilled;
- claims that something is fulfilled;
- claims that something is broken;
- claims that something is abandoned;
- claims that something is blocked;
- claims about laws, votes, government decisions, budgets, contracts, reports, strategies, public procurement, court decisions, regulatory acts, institutional actions, EU procedures, official projects, public consultations, or funding programs.

If a field cannot be verified, return null for scalar fields, [] for list fields, "" only where the schema requires a string and no reliable value exists, and add a warning or source_note explaining the limitation.

MANDATORY SOURCE REVIEW
- Evidence review is the highest priority.
- If program_text is provided, treat it as the primary extraction source unless a fuller official source is provided or linked.
- If program_url is provided and accessible by the model, open and review it as a source. Identify the document title, political subject, program type, period, and source title only when supported by the document.
- If program_url is an HTML page that links to a full PDF, document download, or annex, open and review the full linked document whenever external access allows it.
- If only a URL is provided and the model cannot access external sources in the current runtime, do not pretend to have opened it. Return an empty commitments array unless enough reliable information is present in the URL, notes, or provided text. Add a warning explaining that the URL could not be accessed.
- Prefer primary sources: official party programs, government programs, coalition agreements, parliamentary documents, government decisions, ministry documents, official policy plans, official PDFs, official websites, legal texts, public registers, public procurement records, official budget documents, court acts, regulatory decisions, public institutional records, official project pages, official consultation portals, and EU institutional sources.
- Use secondary sources only for context or when primary sources are unavailable. Mark this limitation in warnings and source_notes.
- Do not stop at the title, summary, press release, or media description if the full text is available.
- If the document contains headings, bullets, tables, numbered priorities, measures, annexes, timelines, financial tables, or implementation plans, review them as potential sources of commitments.
- Do not include any source_urls that were not actually used.
- source_urls must include only sources that materially support extraction or verification.
- source_notes must clearly state what each cited source supports.

MANDATORY FULL-COVERAGE EXTRACTION METHOD
Before producing the final JSON, perform a complete coverage pass:
- Identify all major sections and subsections of the program.
- Review every section and subsection, including annexes, tables, bullets, numbered measures, and appendices.
- For each section, identify all candidate commitments.
- Filter out slogans, rhetoric, values, criticism, and non-checkable claims only after considering whether the nearby text contains concrete measures.
- Remove duplicates only after preserving the strongest original wording and noting duplication in source_notes.
- Keep one commitment per distinct checkable obligation.
- If a paragraph contains multiple independent measures, split them into separate commitments.
- If a broad goal is followed by concrete sub-measures, extract the concrete sub-measures and avoid creating a vague duplicate for the broad goal.
- Preserve exact original wording in original_text.
- Include the source location in source_notes whenever available, such as page number, section title, heading, bullet label, table name, or URL.
- Do not return until every accessible official source document has been reviewed.

COMPLETENESS AND RESPONSE-LIMIT RULE
- Do not silently truncate the commitments array.
- Do not replace unprocessed commitments with a warning while presenting the answer as complete.
- If the complete result cannot fit in one response but the runtime supports continuation, return a valid JSON object for the current batch using the same schema and add a warning such as "Това е партида 1 от N; пълният списък не се побира в един отговор."
- If batching is not supported by the runtime, return the largest valid JSON object possible and include a warning that the result is incomplete due to response-size limits.
- Even when batching is necessary, each batch must contain valid JSON matching the schema and must not contain raw newline characters inside string values.

MANDATORY IMPLEMENTATION VERIFICATION
For each extracted commitment, perform a separate implementation-status verification whenever external access or supplied evidence allows it.

Check, where relevant:
- laws and amendments;
- submitted bills;
- parliamentary votes;
- decisions of Parliament;
- decisions of the Council of Ministers;
- ministry acts and reports;
- budget changes;
- public procurement records;
- contracts and annexes;
- official implementation reports;
- strategies and action plans;
- parliamentary questions and answers;
- official transcripts;
- official press releases;
- court decisions;
- regulator decisions;
- EU procedures or decisions;
- vetoes;
- coalition agreements or disputes;
- publicly available institutional records;
- reliable public statements only when they directly evidence action, abandonment, blockage, or violation.

A status is valid only if source_notes identify the evidence basis.
If status evidence is weak, contradictory, outdated, indirect, not attributable to the political subject, or incomplete, use "insufficient_data" or lower confidence.

ATTRIBUTION AND TIMING STANDARD
- Distinguish evidence that predates the program from evidence that follows it.
- Do not treat an older existing project as fulfillment of a new commitment unless the commitment explicitly continues, expands, funds, or completes that project and the source_notes explain the attribution.
- Do not claim that a political subject fulfilled a commitment merely because a similar policy exists.
- For post-election or post-program status, prefer evidence after the program date or mandate start.
- If a relevant implementation action began before the program but continued after it, describe that limitation in source_notes and adjust confidence downward.
- If the commitment depends on an external actor or international process, distinguish domestic progress from final fulfillment.

WHAT COUNTS AS A COMMITMENT
A commitment is an identifiable promise, intended action, policy measure, reform, target, prohibition, institutional step, funding priority, legislative initiative, administrative action, or measurable outcome that can later be checked against real-world evidence.

Examples of extractable commitments:
- "Introduce electronic health records."
- "Submit amendments to the Judicial System Act."
- "Increase teachers' salaries to 125% of the average salary."
- "Do not increase taxes during the mandate."
- "Build 300 km of new roads."
- "Create a national children's hospital."
- "Reduce administrative burden for small businesses."

Examples that are usually NOT commitments unless supported by concrete measures:
- "We believe in justice."
- "Bulgaria deserves better."
- "We will work for prosperity."
- "The current government failed the people."
- "Healthcare is our priority."
- "We support European values."

GRANULARITY RULES
- Extract one commitment per distinct checkable obligation.
- Do not merge unrelated commitments into a single item just because they appear in the same paragraph.
- Do not split one coherent commitment into many artificial fragments if it would be checked as one policy action.
- If a bullet contains multiple independent measures, extract them as separate commitments.
- If a broad goal is followed by concrete sub-measures, extract the concrete sub-measures and avoid creating an additional vague duplicate for the broad goal.
- If the same commitment appears multiple times in the document, extract it once and mention duplication in source_notes.
- Preserve the original wording in original_text as a concise verbatim excerpt from the source. If the commitment is spread across multiple nearby sentences, include the minimum necessary original wording.
- original_text must contain exact source wording. Do not paraphrase it.
- normalized_description must be short, neutral, and written in plain language.
- title must be concise and suitable for a public checklist item.

PROGRAM METADATA RULES
- program.title: use the official title only if available. Otherwise create a neutral descriptive title and mention the limitation in warnings.
- program.program_type must be one of:
  - "election_program"
  - "government_program"
  - "coalition_agreement"
  - "sector_program"
  - "other"
- program.political_subject_name: use the provided political_subject_name only if reliable, or infer it only if clearly supported by the source. Do not infer it from political context alone.
- program.related_coalition_name: use null unless a coalition is explicitly identified by the source.
- program.period_start and program.period_end: use ISO date format YYYY-MM-DD only when exact dates are available. If only a year or mandate period is known, use the clearest supported value only if it does not create false precision. Otherwise use null and explain in warnings.
- program.source_url: use the provided URL only if relevant to the source. Otherwise null.
- program.source_title: use the official source title only if known from the reviewed source.
- program.description: provide a short neutral description of what the program is, based only on the available source material.

COMMITMENT FIELD RULES
- title: short public-facing title.
- original_text: exact source wording. Do not paraphrase here.
- normalized_description: neutral explanation of what the commitment means in practical terms.
- topic: use a stable topic label such as "healthcare", "education", "judiciary", "energy", "infrastructure", "taxes", "public_finance", "social_policy", "foreign_policy", "security", "anti_corruption", "economy", "environment", "administration", "regional_policy", "digitalization", or "other".
- responsible_institutions: include only institutions explicitly named in the source or directly evidenced by official implementation documents. Do not infer institutions from the policy area alone. Use an empty array if unclear.
- period: include a textual period only when stated or clearly supported by the program context, for example "2025-2029 mandate". Otherwise null.
- deadline: use ISO date format YYYY-MM-DD when exact. If the source gives only a month, year, quarter, or mandate-relative deadline, write a clear textual value without adding false precision. If no deadline exists, return null.
- measurable_criteria: describe how future fulfillment could be checked. If the source gives a numeric, legal, administrative, budgetary, or institutional criterion, preserve it. If no explicit criterion exists but the commitment is still checkable, create a cautious neutral criterion based only on the commitment itself. If no reliable criterion can be formed, return an empty string.
- specificity must be one of:
  - "high"
  - "medium"
  - "low"
- initial_status must be one of:
  - "not_started"
  - "in_progress"
  - "partially_fulfilled"
  - "fulfilled"
  - "broken"
  - "abandoned"
  - "blocked"
  - "insufficient_data"
- confidence_level must be one of:
  - "high"
  - "medium"
  - "low"
  - "insufficient_data"
- confidence_explanation: briefly explain why the extraction and status assessment are reliable or uncertain.
- source_notes: include short notes about source location, exact evidence, ambiguity, duplicate wording, missing deadline, unclear institution, checked implementation evidence, contradictory evidence, or why something was treated as a commitment.

SPECIFICITY STANDARD
- high: concrete action, target, institution, legal measure, funding measure, deadline, prohibition, or measurable outcome is clearly stated.
- medium: the commitment is checkable but lacks some important detail such as deadline, responsible institution, quantitative target, or implementation mechanism.
- low: the text implies a direction or promise but is broad, vague, weakly operationalized, or hard to verify later.
- Do not upgrade specificity because the political goal sounds important.
- Do not downgrade specificity merely because implementation is difficult.

INITIAL STATUS STANDARD
This task includes implementation-status verification. Status is not a placeholder field.

- Use "insufficient_data" unless reliable evidence supports a more specific status.
- Use "not_started" only if a serious evidence review found no visible public implementation actions and source_notes describe what was checked. Do not use "not_started" merely because no action was mentioned in the program text.
- Use "in_progress" only if reliable evidence shows real implementation actions have begun, such as submitted legislation, official working groups, budget allocation, procurement, adopted action plans, administrative measures, institutional decisions, or other concrete steps.
- Use "partially_fulfilled" only if reliable evidence shows that part of the promised result has been achieved, but the commitment is not fully completed.
- Use "fulfilled" only if reliable evidence shows that the promised result has been achieved in substance, not merely announced.
- Use "broken" only when reliable evidence shows that the political subject or responsible governing actor did the opposite of the commitment. Distinguish violation from ordinary non-fulfillment.
- Use "abandoned" only when reliable evidence shows that the commitment is no longer being pursued, has been formally dropped, or has been publicly renounced by the responsible actor.
- Use "blocked" only when reliable evidence identifies an external obstacle such as lack of parliamentary majority, presidential veto, court decision, EU procedure, coalition conflict, budgetary barrier, institutional blockage, regulator decision, or legal impossibility.
- Do not assign politically sensitive statuses such as "broken", "abandoned", or "blocked" by inference alone.
- If evidence is contradictory, incomplete, unavailable, too weak, or not attributable to the commitment, use "insufficient_data".

CONFIDENCE STANDARD
Confidence is about reliability of extraction and verification, not whether the commitment is good, realistic, popular, or likely to be fulfilled.

- high: the commitment is explicit, source wording is clear, key fields are supported by reliable evidence, and status evidence is direct and current.
- medium: the commitment is real and status evidence exists, but some fields require cautious interpretation or evidence is incomplete.
- low: the commitment is extractable but vague, fragmented, context-dependent, only partially supported, status evidence is indirect, or attribution is uncertain.
- insufficient_data: there is not enough reliable source material to make a fair extraction or implementation assessment.

For each commitment:
- If initial_status is anything other than "insufficient_data", source_notes must include the evidence basis for that status.
- If implementation could not be verified, initial_status must be "insufficient_data".
- If the source text supports extraction but not implementation status, confidence_level should usually be "medium", "low", or "insufficient_data" depending on extraction clarity, and confidence_explanation must say that implementation evidence is missing.
- If implementation evidence predates the program or mandate, source_notes must say this and confidence must not be "high" unless there is also direct post-program evidence.

METHODOLOGICAL PROTECTION
- Evaluate concrete commitments, not the entire party, government, coalition, or politician.
- Do not create moral judgments.
- Do not infer bad faith.
- Do not treat political disagreement as evidence that a commitment is false, invalid, broken, or abandoned.
- Do not assume that a commitment is feasible merely because it is promised.
- Do not assume that a commitment is impossible merely because it is ambitious.
- Distinguish clearly between:
  - proven fact;
  - public promise;
  - political interpretation;
  - expert judgment;
  - insufficient information.
- When the evidence is weak, say so through initial_status, confidence_level, confidence_explanation, source_notes, and warnings.
- Every extracted commitment must preserve a traceable path back to the original source wording.
- Every status assessment must preserve a traceable path back to implementation evidence or explicitly say that such evidence is unavailable.

JSON VALIDITY HARD RULES
- The response must be parseable by a strict JSON parser.
- Do not include raw newline characters inside JSON string values.
- If a newline inside a string is unavoidable, encode it as "\\n".
- Prefer single-line string values.
- Escape all internal quotation marks inside string values.
- Do not use trailing commas.
- Do not use comments.
- Do not wrap the JSON in markdown fences.
- Do not add explanatory text before or after the JSON.
- Every opened array and object must be closed.
- The top-level output must be exactly one JSON object.

WARNINGS RULES
Include warnings when:
- the URL cannot be accessed;
- a linked full document, PDF, annex, or download cannot be accessed;
- external verification cannot be performed in the current runtime;
- the program text is incomplete;
- the source appears to be a summary rather than the full program;
- the political subject is unclear or differs from the provided context;
- the program period is unclear;
- the document mixes multiple political subjects;
- commitments are too vague for reliable extraction;
- the source is secondary rather than official;
- there is not enough information to extract commitments safely;
- there is not enough information to assess implementation status;
- status evidence is missing, weak, outdated, indirect, contradictory, or not attributable to the political subject;
- a field was left null, empty, or "insufficient_data" because evidence was unavailable;
- a potentially relevant commitment was rejected because it was too vague, rhetorical, or unsupported;
- the output is incomplete because of response-size or runtime limits.

OUTPUT RULES
- Return only valid JSON matching the exact schema below.
- Do not include markdown.
- Do not include commentary outside the JSON.
- Do not include hidden reasoning.
- Do not include additional keys.
- If no commitments can be safely extracted, return an empty commitments array and explain why in warnings.
- Include source_urls that materially support the extraction or verification, with brief descriptions.
- All user-facing strings must be written in {language}.
- Enum values must remain in English exactly as specified.
- Dates should use ISO format when possible.
- Use null for unknown scalar fields.
- Use [] for unknown list fields.
- Use "" only when the schema requires a string and no reliable value exists.
- Do not use "n/a", "unknown", "not available", "to be checked", "pending", or invented placeholder text.
- Do not use placeholder statuses.
- Do not use default statuses.
- Do not use "not_started" unless evidence review supports it.
- If implementation status was not verified, use "insufficient_data".

The AI response must match this exact JSON schema:
{response_json_schema}

CONTEXT
Prompt version: {prompt_version}
Schema version: {schema_version}
URL: {program_url}
Political subject: {political_subject_name}
Program type: {program_type}
Period: {period}
Additional notes: {notes}

PROGRAM TEXT OR DESCRIPTION
{program_text}
"""
