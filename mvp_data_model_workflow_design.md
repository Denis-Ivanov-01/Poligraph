# MVP Data Model & Workflow Design

## 1. Context

This document summarizes the MVP database and workflow design for the political transparency platform.

The platform is currently in alpha. The database is being redesigned from scratch, without backward compatibility requirements.

The product has three main content modules:

1. **Statements**  
   Focus: How politicians speak.

2. **Programs and commitments**  
   Focus: What political actors promise and what they implement.

3. **Cases**  
   Focus: What the factual picture is around important public issues.

The backend stack is:

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Redis
- Jinja2 server-rendered internal pages

The public frontend stack is:

- React
- TypeScript
- Vite
- React Router

---

## 2. Core product assumptions

### 2.1. AI does not access the system

In the MVP, AI has no direct access to:

- the backend;
- the database;
- internal platform records;
- existing DB IDs;
- system state.

The AI workflow is manual and external.

### 2.2. AI output is not database truth

AI returns a structured JSON response. That response is treated as an import package, not as trusted canonical database state.

The backend parses the JSON and creates normalized database records.

Temporary AI refs such as `C1`, `C2`, `S1`, `S2` are local JSON refs only. They are not database IDs.

### 2.3. Publishing is not factual approval

The MVP moderator does not manually fact-check every claim or source.

The moderator checks only:

- whether the JSON is valid;
- whether required fields exist;
- whether the structure is not broken;
- whether there are no obvious massive structural problems.

This is called **structural review**.

Factual review is a separate later workflow.

Therefore:

- published does not mean factually verified;
- structural review does not mean factual approval;
- AI-generated verification statuses must be clearly stored as AI-generated;
- the public UI must not imply that every source was manually fact-checked.

---

## 3. Key design principles

## 3.1. Normalize anything that must be queried or displayed

Raw AI JSON is stored, but important data is also parsed into normalized tables.

Normalize:

- statement analyses;
- extracted claims;
- evidence items;
- claim-evidence links;
- programs;
- program sections;
- commitments;
- commitment status updates;
- cases;
- case timeline events;
- case fact points.

## 3.2. Keep raw AI input and output

Every AI session should preserve:

- generated prompt;
- prompt version;
- schema version;
- model name when available;
- raw AI response pasted by the moderator;
- parsed JSON;
- parse error if parsing fails.

## 3.3. Use a shared evidence layer

Sources and documents should not be duplicated across separate module-specific evidence tables.

Use:

- `evidence_items`

and link tables:

- `statement_claim_evidence_links`;
- `commitment_evidence_links`;
- `case_timeline_event_evidence_links`;
- `case_fact_point_evidence_links`.

## 3.4. Do not store overall score

The platform may show an overall score, but it is a derived UI value.

The database stores only the four dimension scores:

- factual accuracy;
- logical consistency;
- communicational integrity;
- principle consistency.

The UI computes the overall score from these four criteria.

## 3.5. Claim materiality matters

Not all claims have equal importance.

A central claim about the Constitution, courts, elections, public finances, corruption, public health, national security, legislation, or public funds should weigh more than peripheral background details.

Therefore, `statement_claims` includes:

- `materiality`;
- `materiality_reason`.

---

## 4. Statement analysis workflow

### Step 1: Create statement

A moderator creates a statement in the internal app.

The moderator provides:

- title;
- source type;
- optional source URL;
- original text;
- statement date;
- politician;
- party at statement time;
- optional notes.

The statement starts as:

```text
status = draft
```

### Step 2: Generate AI prompt

The backend generates a prompt based on:

- platform methodology;
- statement metadata;
- original statement text;
- expected JSON schema;
- previous statements sample for principle consistency.

The backend creates an `ai_runs` row:

```text
target_type = statement
target_id = statement.id
task_type = statement_analysis
execution_mode = manual_external
status = prompt_generated
```

The moderator copies this prompt manually.

### Step 3: External AI analysis

The moderator pastes the prompt into an external AI model.

The AI returns a structured JSON response.

### Step 4: Paste JSON into internal app

The moderator pastes the AI JSON response into an internal input box.

The backend:

- saves the raw response;
- attempts to parse it;
- validates the expected structure;
- stores parse errors if parsing fails.

### Step 5: Parse into normalized records

If JSON parsing succeeds, the backend creates:

- `statement_ai_analyses`;
- `statement_claims`;
- `evidence_items`;
- `statement_claim_evidence_links`.

AI refs are mapped only during parsing:

```text
AI claim_ref C1 -> statement_claims.id
AI source_ref S1 -> evidence_items.id
```

The AI refs remain stored as `import_ref`, but they are not database IDs.

### Step 6: Structural review

The moderator performs structural review only.

Possible outcomes:

- passed;
- failed;
- needs fix.

This does not mean factual approval.

### Step 7: Publish

If structural review passes, the moderator can publish.

Publishing sets the statement and analysis to published, but keeps factual review statuses as `not_reviewed` unless changed later by a separate factual review workflow.

---

## 5. AI response design

The statement AI JSON is expected to contain:

```json
{
  "model_name": "string",
  "prompt_version": "mvp-3",
  "schema_version": "mvp-3",
  "statement_analysis": {
    "factual_accuracy_applicability": "applicable",
    "scores": {
      "factual_accuracy": 80,
      "logical_consistency": 75,
      "communicational_integrity": 70,
      "principle_consistency": 100
    },
    "explanations": {
      "factual_accuracy": "string",
      "logical_consistency": "string",
      "communicational_integrity": "string",
      "principle_consistency": "string"
    },
    "evidence_review_completeness": "partial",
    "human_review_recommended": false,
    "human_review_reason": null
  },
  "claims": [
    {
      "claim_ref": "C1",
      "exact_quote": "string",
      "normalized_claim": "string",
      "claim_type": "factual",
      "checkability": "checkable",
      "materiality": "high",
      "materiality_reason": "string",
      "ai_verification_status": "supported",
      "confidence_level": "high",
      "evidence_summary": "string",
      "missing_or_uncertain_evidence": null,
      "used_for_dimensions": ["factual_accuracy"],
      "source_refs": ["S1"]
    }
  ],
  "sources": [
    {
      "source_ref": "S1",
      "title": "string",
      "url": "string",
      "source_type": "government_document",
      "publisher": "string",
      "published_at": "YYYY-MM-DD or null",
      "quote_or_relevant_excerpt": "string",
      "description": "string",
      "reliability_level": "high"
    }
  ]
}
```

Important parser rules:

- `claim_ref` is temporary.
- `source_ref` is temporary.
- DB IDs are generated by the database.
- `factual_accuracy` may be `null` when `factual_accuracy_applicability = not_applicable`.
- No overall score is returned by AI.
- No backend-only workflow fields should be returned by AI.

---

## 6. Main database tables

## 6.1. Users and audit

### `users`

Stores internal users.

Key fields:

- username;
- email;
- password hash;
- global role;
- active status;
- login/change timestamps.

Roles:

```text
admin
moderator
viewer
```

### `audit_logs`

Stores actions performed in the system.

Used for:

- create;
- update;
- parse;
- structural review;
- publish;
- delete/archive;
- restore.

### `entity_revisions`

Stores snapshots of important entities for traceability and possible rollback.

---

## 6.2. Political core

### `political_parties`

Stores parties.

### `politicians`

Stores politicians.

### `party_memberships`

Stores politician-party membership over time.

This supports determining party affiliation at statement time.

---

## 6.3. Media

### `media_assets`

Stores uploaded media files.

### `statement_media_assets`

Many-to-many relation between statements and media assets.

---

## 6.4. AI runs

### `ai_runs`

Generic table for AI sessions.

In MVP, AI runs usually represent manual external AI sessions.

Important fields:

- target type;
- target ID;
- task type;
- execution mode;
- status;
- model name;
- prompt version;
- schema version;
- prompt text;
- raw AI response;
- parsed JSON;
- parse error;
- structural review status;
- factual review status;
- user/timestamp fields.

Execution modes:

```text
manual_external
api_call
```

MVP uses:

```text
manual_external
```

---

## 6.5. Evidence

### `evidence_items`

Shared source/document table.

Used by statements, commitments, and cases.

Evidence items may be:

- manually created;
- AI-imported;
- imported from another workflow.

Important fields:

- title;
- URL;
- archive URL;
- source type;
- publisher;
- publication date;
- excerpt;
- description;
- reliability level;
- source origin;
- structural status;
- factual review status.

AI-imported evidence is not manually fact-checked by default.

---

## 6.6. Statements

### `statements`

Stores the original political statement and its metadata.

Important fields:

- title;
- slug;
- source type;
- source URL;
- original text;
- statement date;
- politician;
- party at statement time;
- status;
- selection reason;
- topic;
- public interest level;
- checkability level;
- internal notes;
- publication fields.

### `statement_ai_analyses`

Stores the structured analysis result for a statement.

Stores the four dimension scores and explanations:

- factual accuracy;
- logical consistency;
- communicational integrity;
- principle consistency.

Does not store overall score.

Also stores:

- factual accuracy applicability;
- evidence review completeness;
- human review recommendation;
- structural review status;
- factual review status;
- publication fields.

### `statement_claims`

Stores extracted claims or meaningful analytical units.

Important fields:

- import ref;
- display code;
- exact quote;
- normalized claim;
- claim type;
- checkability;
- materiality;
- materiality reason;
- AI verification status;
- confidence level;
- evidence summary;
- missing/uncertain evidence;
- dimensions used for;
- source origin;
- structural status;
- factual review status;
- display order.

### `statement_claim_evidence_links`

Connects statement claims to evidence items.

Relation types:

```text
supports
contradicts
contextualizes
limits
neutral
```

---

## 6.7. Appeals

### `appeals`

Stores public or internal feedback about possible mistakes, missing context, or disputed analysis.

Can be connected to:

- statement;
- program;
- commitment;
- case.

---

## 6.8. Programs

### `programs`

Stores political programs, government programs, coalition agreements, election programs, and similar documents.

Program types:

```text
government_program
coalition_agreement
party_program
election_program
policy_platform
government_action_plan
sector_strategy
municipal_program
legislative_agenda
other
```

### `program_sections`

Preserves the original structure of a program.

Useful for:

- display;
- section-by-section AI extraction;
- connecting commitments to program sections.

### `program_ai_extractions`

Stores structured result metadata for AI extraction of commitments from programs.

---

## 6.9. Commitments

### `commitments`

Stores individual promises, goals, measures, or commitments extracted from programs.

Important fields:

- program;
- program section;
- title;
- original text;
- normalized description;
- topic;
- responsible institutions text;
- period;
- deadline;
- measurable criteria;
- current status;
- status group;
- status explanation;
- confidence;
- materiality;
- key commitment flag;
- publication fields.

Commitment statuses:

```text
not_started
in_progress
partially_fulfilled
fulfilled
violated
abandoned
unclear
```

Status groups:

```text
pending
active
completed
failed
unclear
```

### `commitment_status_updates`

Stores the history of commitment status changes.

The current status is denormalized on `commitments`, but the history is preserved here.

### `commitment_evidence_links`

Connects commitments or status updates to evidence items.

Relation types:

```text
supports_status
contradicts_status
contextualizes
proves_completion
proves_delay
proves_violation
background
```

---

## 6.10. Cases

### `cases`

Stores public-interest cases.

A case is a structured factual dossier, not just an article.

Important fields:

- title;
- slug;
- sector;
- short summary;
- full description;
- public interest reason;
- status;
- importance level;
- publication fields.

Case statuses:

```text
monitoring
active_debate
institutional_review
resolved
archived
```

### `case_timeline_events`

Stores chronology.

Answers:

```text
What happened and when?
```

### `case_timeline_event_evidence_links`

Connects timeline events to evidence items.

### `case_fact_points`

Stores the evidentiary picture of a case.

Answers:

```text
What do we know?
What is disputed?
What do we not know?
```

Point types:

```text
known
disputed
unknown
```

### `case_fact_point_evidence_links`

Connects case fact points to evidence items.

### `case_statements`

Connects cases to related statements.

### `case_commitments`

Connects cases to related commitments.

---

## 6.11. Cross-module links

### `statement_commitments`

Connects statements to commitments.

Useful when a politician:

- mentions a commitment;
- promises something;
- claims progress;
- denies delay;
- attacks a commitment;
- explains a commitment.

---

## 6.12. Imports

### `imports`

Stores batch import metadata.

### `import_items`

Stores individual imported items and their parse/import state.

Useful for future AI-generated JSON imports, program imports, commitment imports, and structured data workflows.

---

## 7. Internal UI requirements

The internal Jinja2 app should support the statement workflow:

1. Create/edit statement.
2. Generate prompt.
3. Copy prompt.
4. Paste AI JSON response.
5. Parse and validate response.
6. Show parse errors.
7. Preview parsed analysis:
   - scores;
   - explanations;
   - claims;
   - sources;
   - claim-source links.
8. Perform structural review.
9. Publish.

Internal wording should use:

```text
Structural review
Publish
AI-generated analysis
Factual review: not reviewed / pending / reviewed / disputed / corrected
```

Avoid wording that implies manual fact-check approval.

---

## 8. Public frontend requirements

The public frontend should show statement analysis with:

- statement metadata;
- four dimension scores;
- UI-computed overall score;
- explanations;
- extracted claims;
- materiality;
- AI verification status;
- confidence level;
- sources;
- disclaimer.

Recommended disclaimer:

> This analysis was generated with AI according to the platform methodology and passed structural moderation review. This does not mean every source was manually fact-checked by a moderator. If an error is found, the analysis may be corrected.

The frontend may compute overall score from the four dimensions. The database should not store overall score.

---

## 9. Non-goals for MVP

Do not implement in this MVP redesign:

- direct AI API integration;
- group/permission matrix;
- external signals;
- normalized institutions;
- aggregate party or politician scores;
- automated factual review;
- complete human fact-check workflow;
- advanced dashboards.

---

## 10. Future extension points

The design intentionally allows future expansion into:

- direct AI API calls;
- deeper factual review workflow;
- normalized institutions;
- external evidence sources and signals;
- group-based permissions;
- aggregate metrics;
- richer case dossiers;
- stronger cross-module profile summaries for politicians and parties.

These are not MVP requirements, but the schema should not block them.

---

## 11. Summary

The MVP design is based on a clear distinction between:

```text
AI-generated structure
```

and

```text
human-verified factual truth
```

The platform uses AI to structure political speech, extract claims, propose source-backed analysis, and generate consistent evaluations.

The backend stores raw AI output and normalized parsed records.

The moderator performs structural review and publishes.

Factual review remains a separate later workflow.

This gives the platform a strong alpha-stage foundation without pretending that every published AI-generated analysis has already been manually fact-checked.
