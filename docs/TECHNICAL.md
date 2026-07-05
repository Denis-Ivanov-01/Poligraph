# Technical Documentation

## Overview

Political AI Filter is a monorepo with two application surfaces:

- a public read-only platform for browsing analyzed political statements;
- an internal moderation/admin interface for trusted users.

The repository also contains shared public content, including the methodology Markdown used by the frontend.

## Architecture

The current implementation includes:

- `backend/` - FastAPI backend with SQLAlchemy models, Alembic migrations, PostgreSQL, Redis, and Jinja2 templates for the internal interface.
- `frontend/` - React, TypeScript, and Vite public frontend.
- `frontend/src/content/` - editable Markdown content, including the methodology document rendered on the public methodology page.
- `docker-compose.yml` - local development stack for PostgreSQL, Redis, backend, and frontend.

The public frontend consumes read-only API endpoints under `/api/*`. Internal moderation workflows are served by the backend under `/internal`.

## Main application areas

### Public routes and pages

The public React app currently includes routes for:

- `/` - home page
- `/parties` and `/parties/:slug`
- `/politicians` and `/politicians/:slug`
- `/statements` and `/statements/:id`
- `/dashboard`
- `/methodology`
- `/search`

The public API includes routers for parties, politicians, statements, dashboard data, and search.

### Internal moderator/admin routes

The backend includes internal routes under `/internal`, including:

- authentication and internal home;
- party management;
- politician management;
- statement creation/editing;
- AI prompt and JSON workflow;
- moderator management;
- audit logs;
- appeals placeholder/workflow area.

These routes are intended for trusted users only.

### Shared components and content

The public frontend uses reusable statement, score, party, politician, layout, and common UI components. Public UI strings are stored in `frontend/src/resources.json` and exposed through `frontend/src/i18n/resources.ts`.

The methodology page renders Markdown from `frontend/src/content/methodology.bg.md` using `react-markdown` and `remark-gfm`.

## Analysis data flow

The intended analysis workflow is:

1. A moderator adds the source and raw statement text.
2. The system stores the original text and statement metadata.
3. The statement is analyzed using a versioned instruction/prompt.
4. The AI model returns structured output.
5. The raw model response is stored.
6. A moderator reviews the result for obvious technical, factual, or structural issues.
7. Approved analysis becomes visible on the public platform.

Raw prompt/instruction text and raw model responses should be preserved for auditability. Public statement detail pages can then show how a published analysis was produced, instead of presenting only final scores.

## Internal moderation interface

The internal interface is for trusted administrators and moderators only.

Security notes:

- protect internal routes with authentication;
- protect write APIs and mutation routes;
- never expose admin credentials;
- never commit secrets;
- use environment variables or secret management for production configuration;
- do not make internal tools accessible from the public web without authentication;
- replace development credentials before deployment.

## Environment variables

The repository includes `.env.example`. Current variables include:

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

Do not commit real secrets. Internal moderation credentials, AI API keys, and write-access configuration should be stored securely.

## Local development

From the repository root:

```bash
cp .env.example .env
docker compose up --build
```

Local services:

- Backend API: `http://localhost:8000`
- Public frontend: `http://localhost:5173`
- Internal app: `http://localhost:8000/internal`

Frontend commands from `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run preview
```

Backend commands from `backend/`:

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The backend package targets Python 3.12 or newer.

## Build and deployment

The frontend production build is:

```bash
npm run build
```

The backend Dockerfile runs Alembic migrations and starts Uvicorn. The local Docker Compose stack is suitable for development, not a complete production deployment plan.

Deployment assumptions are still evolving. Production deployments should explicitly configure secrets, database access, Redis access, CORS origins, media storage, internal route exposure, logging, and backups.

## Documentation links

- [Root README](../README.md)
- [Methodology rationale](./METHODOLOGY.md)
