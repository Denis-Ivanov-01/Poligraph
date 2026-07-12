# Political AI Filter

Political AI Filter is an open-source civic-tech project for transparent AI-assisted analysis of public political statements.

The platform evaluates specific political statements, not politicians as people and not ideologies as "right" or "wrong". It looks at four dimensions:

- Factual accuracy
- Logical consistency
- Communicational integrity
- Principle consistency

The goal is to make political speech more inspectable. It is not to tell people who to vote for.

## TODOs
From system standpoint:
- Implement advanced moderator rights restriction - mods must be able to edit only their posts, to be assigned only some politicians, parties, etc.
- Moderator actions must be reversible by the administrator
- Add contacts page and github repo link in the home page
- All accessible from the UI methods for import/deleting/other actions must be easily accessible from REST to enable future automation. A better safety-wise alternative is to have a python API without exposing it to REST.
- All endpoints must be protected by credentials to enable ease of future autiomation while maintaning security.
- All credentials-related stuff must be encrypted.
- Each list in the internal app (statements, commitments, programs...) must have a checkbox for each item for batch deletion and other actions
- After mods log in their account, they must be able to change their password from the internal site

From AI workflow standpoint:
- The political program workflow should support: AI-generated JSON with summaries for all the commitments. Then there should be a dedicated page for each commitment. There must be an option for multiple commitments to be imported all at once.
- For all entities that have forms for filling out, at the bottom there must be an input box for JSONs so even this can be easily automated.
- Design a semi automated workflow that allows moderators to track progress on political programs for each goal/sub-goal (commitment). Each modertor will be in charge of multiple things so there must be a (official or unofficial) way to keep track of checked things

## Why this project exists

Political speech often reaches people as a mix of facts, arguments, promises, accusations, framing, and selective context. A statement can contain accurate facts but still lead to a weak conclusion. It can sound confident while leaving out context that matters. It can also be consistent with a politician's earlier position, or quietly depart from it.

This project exists to make public political statements easier to inspect. Instead of asking only whether someone likes a politician or agrees with a party, the platform asks a narrower question: what does this specific public statement give the citizen?

The aim is not to remove political disagreement. Disagreement is part of democracy. The aim is to help that disagreement start from clearer facts, better arguments, and a more visible record of how each analysis was produced.

## What the platform evaluates

- **Factual accuracy** - are verifiable factual claims supported by reliable evidence?
- **Logical consistency** - do the conclusions follow from the premises?
- **Communicational integrity** - is the information presented in a way that does not materially mislead?
- **Principle consistency** - is the position consistent with previous public positions on the same issue?

## What the platform does not evaluate

The project does not try to decide which ideology is correct, whether a political position is desirable, or whether a politician is a good person. It focuses on something narrower and more inspectable: how a specific public statement is constructed, supported, argued, communicated, and connected to previous positions.

## How each analysis is produced

Each published analysis should leave an audit trail:

1. The original statement text is copied from a public and verifiable source.
2. The statement is analyzed using a visible instruction to the AI model.
3. The selected AI model returns a structured response.
4. The raw model response is stored and made available.
5. A moderator reviews the result for obvious technical, factual, or structural problems.
6. If the review is passed, the analysis is published.

AI models are not perfectly deterministic. The same model can sometimes produce slightly different answers, and different models can differ more. The project does not claim perfect or final automated truth. The goal is a transparent and inspectable process.

## Applications included in this repository

This repository includes both the public read-only platform and the internal moderator/admin interface.

### Public platform

The public platform is a read-only interface for browsing analyzed statements, politicians, parties, rankings, methodology, and transparency information.

### Internal moderation interface

The internal interface is a web application for trusted administrators and moderators. It may include:

- managing parties;
- managing politicians;
- adding statement sources and raw statement text;
- generating or storing AI analysis results;
- reviewing raw model outputs;
- approving or rejecting analyses before publication.

The internal interface is not intended for public access and must be protected in production.

## Documentation

- [Technical documentation](./docs/TECHNICAL.md)
- [Methodology rationale](./docs/METHODOLOGY.md)
- [Program commitment analysis workflow](./docs/program_commitment_analysis_v6.md)

The technical documentation covers architecture, setup, data flow, environment variables, moderation workflow, and deployment assumptions.

The methodology rationale covers the evaluation criteria, the role of AI, limitations, uncertainty handling, correction policy, and source standards.

## Future Development Directions

### 1. Promise-vs-action analysis

The project may expand from isolated statement analysis toward comparing political promises with later actions, votes, decisions, public records, and institutional outcomes.

This would make it easier to track whether politicians and parties follow through on stated commitments. It is a natural extension of principle consistency, but broader: it compares speech with real-world action, not only speech with previous speech.

### 2. Safer and more automated analysis

The project should gradually move toward more automated analysis while reducing unnecessary manual moderator workload. This needs to happen incrementally and safely.

Future automation should preserve:

- auditability;
- raw input/output visibility;
- model and prompt versioning;
- confidence and uncertainty handling;
- fallback to human review;
- checks for obvious technical, factual, or structural errors;
- conservative publishing rules for high-risk or low-confidence analyses.

The direction is not to remove moderators entirely. The direction is to reduce repetitive manual work while keeping the process reliable, transparent, and low-risk.

## Tech stack

This section reflects the current implementation and should be updated as the architecture evolves.

- **Backend:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, Jinja2 server-rendered internal pages
- **Frontend:** React, TypeScript, Vite, React Router
- **Content:** editable Markdown methodology content rendered in the public frontend
- **Local development:** Docker Compose

## Local development

Copy the example environment file:

```bash
cp .env.example .env
```

Start the local stack:

```bash
docker compose up --build
```

Local services:

- Backend API: `http://localhost:8000`
- Public frontend: `http://localhost:5173`
- Internal app: `http://localhost:8000/internal`

The frontend can also be run from `frontend/`:

```bash
npm install
npm run dev
npm run build
```

The backend can also be run from `backend/` after installing the Python package dependencies:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Environment variables

The repository includes `.env.example`. Do not commit real secrets.

Important configuration currently includes:

- `DATABASE_URL`
- `REDIS_URL`
- `APP_ENV`
- `APP_SECRET_KEY`
- `SESSION_COOKIE_NAME`
- `ROOT_ADMIN_USERNAME`
- `ROOT_ADMIN_PASSWORD_HASH`
- `ROOT_ADMIN_ENABLED`
- `PUBLIC_BASE_URL`
- `BACKEND_BASE_URL`
- `MEDIA_STORAGE_PATH`
- `CORS_ALLOWED_ORIGINS`
- `VITE_API_BASE_URL`
- `VITE_PUBLIC_BASE_URL`

Internal moderation credentials, AI API keys, and any write-access configuration must be stored securely. For production, replace development defaults such as `ROOT_ADMIN_PASSWORD_HASH=plain:admin` and use a strong `APP_SECRET_KEY`.

## Project status

The project is in early development.

Current priorities include:

- public statement pages;
- politician and party pages;
- transparent AI analysis workflow;
- methodology page;
- internal moderation workflow;
- score aggregation and ranking logic;
- source and evidence traceability.

## Contributing

Contributions are welcome. Useful areas include:

- UI/UX;
- methodology wording;
- technical architecture;
- moderation workflow;
- security review;
- accessibility;
- source transparency;
- tests;
- documentation.

Please keep changes focused, transparent, and respectful of the civic purpose of the project.

## Responsible use

This project should not be used to harass, defame, or target individuals. The goal is to improve the quality of public political discourse by making claims, arguments, context, and inconsistencies easier to inspect.

## License

The source code is licensed under the MIT License.

The methodology and original documentation may be licensed separately under CC BY 4.0 unless otherwise stated.

Third-party political statements, quoted materials, external sources, media excerpts, and linked documents are not covered by this repository's license and remain under their respective owners' rights.
