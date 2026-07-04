# Political AI Filter

Monorepo MVP for a public read-only political statement analysis platform.

## Architecture

- `backend/`: FastAPI, SQLAlchemy, Alembic, PostgreSQL, Redis, server-rendered `/internal`.
- `frontend/`: React, TypeScript, Vite public website.
- Public frontend consumes only `/api/*`.
- Internal moderator/root-admin workflows live under `/internal`.

## Local Development

1. Copy `.env.example` to `.env`.
2. Run:

```bash
docker compose up --build
```

Services:

- Backend: `http://localhost:8000`
- Public frontend: `http://localhost:5173`
- Internal app: `http://localhost:8000/internal`

Development root admin defaults from `.env.example`:

- Username: `admin`
- Password: `admin`

For production, replace `ROOT_ADMIN_PASSWORD_HASH` with an Argon2 hash and set a strong `APP_SECRET_KEY`.

## Public API

Read-only endpoints:

- `GET /api/parties`
- `GET /api/parties/{slug}`
- `GET /api/politicians`
- `GET /api/politicians/{slug}`
- `GET /api/statements`
- `GET /api/statements/{id}`
- `GET /api/dashboard`
- `GET /api/search?q=...`

Public endpoints exclude drafts, archived/deleted statements, internal notes, moderator data, audit logs, and unpublished AI analyses.

## Internal Workflow

1. Root Admin logs in at `/internal/login`.
2. Root Admin creates moderators.
3. Moderator creates parties, politicians, and draft statements.
4. Moderator generates an AI prompt.
5. Moderator pastes AI JSON.
6. Valid AI JSON creates or replaces `ai_analyses`.
7. Publishing makes the statement and AI analysis visible through the public API.
8. Sensitive internal actions are written to `audit_logs`.
