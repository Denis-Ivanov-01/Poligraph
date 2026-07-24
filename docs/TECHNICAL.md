# Technical Documentation

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Application Areas](#application-areas)
- [Public Frontend](#public-frontend)
- [Backend and Internal App](#backend-and-internal-app)
- [Analysis Data Flow](#analysis-data-flow)
- [Content and Localization](#content-and-localization)
- [Umami Analytics and Diagnostics](#umami-analytics-and-diagnostics)
- [Environment Variables](#environment-variables)
- [Local Development](#local-development)
- [Build and Deployment](#build-and-deployment)
- [Security Notes](#security-notes)
- [Documentation Links](#documentation-links)

## Overview

Political AI Filter is an open-source civic-tech monorepo with two main surfaces:

- a public read-only React application for browsing analyzed political statements, political programs, commitments, politicians, parties, rankings, methodology, and transparency information;
- an internal FastAPI/Jinja2 moderation and administration interface for trusted users.

The repository also includes editable public content, shared resource files, Docker-based local infrastructure, and an optional internal analytics diagnostics panel.

## Architecture

The current implementation includes:

- `backend/` - FastAPI backend with SQLAlchemy models, Alembic migrations, PostgreSQL, Redis, internal Jinja2 templates, and public API routers.
- `frontend/` - React, TypeScript, Vite, and React Router public frontend.
- `frontend/src/content/` - editable Markdown content, including the public methodology document.
- `frontend/src/resources.json` - public frontend strings used through `frontend/src/i18n/resources.ts`.
- `backend/app/resources.json` - backend resource values used by backend services, including AI prompt language configuration.
- `docker-compose.yml` - local development stack for PostgreSQL, Redis, backend, frontend, Umami, and Umami PostgreSQL.

The public frontend consumes read-only API endpoints under `/api/*`. Internal moderation workflows are served by the backend under `/internal`. The diagnostics panel is protected separately at `/diagnostics_panel` by default.

## Application Areas

### Public routes and pages

The public React app currently includes routes for:

- `/` - public home page;
- `/dashboard` - public dashboard, previously the home-page style overview;
- `/parties` and `/parties/:slug`;
- `/politicians` and `/politicians/:slug`;
- `/statements` and `/statements/:id`;
- `/programs`, `/programs/:id`, `/programs/:programId/commitments/:slug`, and `/programs/commitments/:slug`;
- `/methodology`;
- `/search`;
- `*` - not-found page.

The public API includes routers for dashboard data, parties, politicians, programs, statements, and search.

### Internal moderator/admin routes

The backend includes internal routes under `/internal`, including:

- authentication and internal home;
- party management;
- politician management;
- statement creation/editing;
- program, section, and commitment management;
- AI prompt and JSON workflow;
- moderator management;
- audit logs;
- appeals placeholder/workflow area.

The internal diagnostics panel is mounted at `/diagnostics_panel` by default and can also be exposed at a configured path with `DIAGNOSTICS_PANEL_PATH`.

## Public Frontend

The public frontend is a Vite React app. Routing is defined in `frontend/src/app/router.tsx`, with `PublicLayout` wrapping shared layout, navigation, footer, and optional analytics.

Key frontend conventions:

- Page-level copy should come from `frontend/src/resources.json` unless it is database content or long-form Markdown content.
- Long-form methodology content lives in `frontend/src/content/methodology.bg.md`.
- The methodology page renders Markdown through `react-markdown` and `remark-gfm`.
- Shared UI elements live under `frontend/src/components/`.
- Public API clients live under `frontend/src/api/`.

## Backend and Internal App

The backend is a FastAPI application with:

- SQLAlchemy ORM models in `backend/app/models/`;
- Pydantic schemas in `backend/app/schemas/`;
- public routers in `backend/app/routers/public/`;
- internal routers in `backend/app/routers/internal/`;
- shared services in `backend/app/services/`;
- internal Jinja2 templates in `backend/app/templates/internal/`;
- internal CSS in `backend/app/static/internal.css`.

Configuration is loaded through `backend/app/config.py` using Pydantic settings. Docker Compose passes the local development values directly into the backend container.

## Analysis Data Flow

The intended statement analysis workflow is:

1. A moderator adds the source and raw statement text.
2. The system stores the original text and statement metadata.
3. The statement is analyzed using a versioned instruction/prompt.
4. The prompt template is assembled from `backend/app/services/ai_prompt_template.py`.
5. Backend resource values, such as the target language, are read from `backend/app/resources.json`.
6. The AI model returns structured output.
7. The raw model response is stored.
8. A moderator reviews the result for obvious technical, factual, or structural issues.
9. Approved analysis becomes visible on the public platform.

Raw prompt/instruction text and raw model responses should be preserved for auditability. Public statement detail pages can then show how a published analysis was produced, instead of presenting only final scores.

Political program analysis uses a separate workflow for program structure and commitment status. Moderators can generate prompts, import validated AI JSON, review section and commitment structure, process commitment analysis in batches, and publish reviewed programs and commitments. The detailed program workflow is documented in [`docs/program_commitment_analysis_v6.md`](./program_commitment_analysis_v6.md).

## Content and Localization

The project uses file-backed content/resources so that copy can be edited without rewriting business logic.

- Public UI strings: `frontend/src/resources.json`
- Public resource accessor: `frontend/src/i18n/resources.ts`
- Backend resources: `backend/app/resources.json`
- Backend resource accessor: `backend/app/resources.py`
- Methodology long-form content: `frontend/src/content/methodology.bg.md`
- Statement methodology notes: `docs/STATEMENTS_METHODOLOGY.md`
- Political program methodology notes: `docs/PPROGRAMS_METHODOLOGY.md`

Short UI strings should generally go into `resources.json`. Long public editorial content should remain in Markdown or another dedicated content file.

## Umami Analytics and Diagnostics

Umami is a lightweight, privacy-friendly web analytics application. In this repository it is not a FastAPI library and not a frontend package dependency. It runs as a separate Docker service with its own PostgreSQL database.

The local Docker stack includes:

- `umami` - the Umami analytics app, exposed at `http://localhost:3000`;
- `umami-db` - PostgreSQL storage for Umami;
- `backend` - embeds a configured shared Umami dashboard in the internal diagnostics panel;
- `frontend` - optionally loads the Umami tracking script for the public app.

### Purpose

Umami is used for internal traffic diagnostics:

- page views;
- visited public routes;
- referrers and basic traffic trends;
- high-level usage patterns for the public app.

The diagnostics panel is internal-only and is not linked in the public frontend.

### Internal diagnostics panel

The diagnostics panel is controlled by:

```env
DIAGNOSTICS_PANEL_ENABLED=true
DIAGNOSTICS_PANEL_PATH=/diagnostics_panel
DIAGNOSTICS_DASHBOARD_URL=http://localhost:3000/share/your-share-id
```

`DIAGNOSTICS_PANEL_ENABLED` only enables the page. `DIAGNOSTICS_DASHBOARD_URL` must be set to a real Umami Share URL before the panel can embed analytics.

To create the Share URL:

1. Open `http://localhost:3000`.
2. Log into Umami.
3. Add or open the website for the public app.
4. Enable sharing for the dashboard/view you want to embed.
5. Copy the generated Share URL into `DIAGNOSTICS_DASHBOARD_URL`.
6. Restart the backend container.

```bash
docker compose up -d backend
```

### Public page tracking

The public app already has automated tracking script injection through `frontend/src/components/layout/UmamiAnalytics.tsx`.

Enable it with:

```env
NEXT_PUBLIC_UMAMI_ENABLED=true
NEXT_PUBLIC_UMAMI_SCRIPT_URL=http://localhost:3000/script.js
NEXT_PUBLIC_UMAMI_WEBSITE_ID=your-website-id
```

After changing these values, restart the frontend container:

```bash
docker compose up -d frontend
```

Once enabled, `PublicLayout` renders the Umami script on every public route. Umami automatically tracks page views and single-page-app navigations, so the project does not need per-page tracking code for normal route views.

The only part that is not currently fully automated is creating the Umami website and Share URL, because those IDs are generated inside Umami. After those values are copied into `.env`, tracking and diagnostics embedding are automatic on container restart.

Useful local URLs:

- Umami app: `http://localhost:3000`
- Public frontend: `http://localhost:5173`
- Diagnostics panel: `http://localhost:8000/diagnostics_panel`

Official Umami references:

- [Install Umami](https://docs.umami.is/docs/install)
- [Collect data](https://docs.umami.is/docs/collect-data)
- [Tracker configuration](https://docs.umami.is/docs/tracker-configuration)
- [Enable Share URL](https://docs.umami.is/docs/enable-share-url)

## Environment Variables

The repository includes `.env.example`. Current variables include:

### Core backend

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

### Frontend

- `VITE_API_BASE_URL`
- `VITE_PUBLIC_BASE_URL`

### Umami

- `UMAMI_DATABASE_PASSWORD`
- `UMAMI_APP_SECRET`
- `NEXT_PUBLIC_UMAMI_ENABLED`
- `NEXT_PUBLIC_UMAMI_SCRIPT_URL`
- `NEXT_PUBLIC_UMAMI_WEBSITE_ID`

### Diagnostics

- `DIAGNOSTICS_PANEL_ENABLED`
- `DIAGNOSTICS_PANEL_PATH`
- `DIAGNOSTICS_DASHBOARD_URL`

Do not commit real secrets. Internal moderation credentials, AI API keys, analytics secrets, and write-access configuration should be stored securely.

## Local Development

This quick start is Windows-oriented and assumes Docker Desktop is installed and running.

### Prerequisites

- Git
- Docker Desktop

Clone the repository:

```powershell
git clone https://github.com/Denis-Ivanov-01/Poligraph.git
cd Poligraph
```

Copy the example environment file and start the local Docker stack:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

The first start builds the backend and frontend images, starts PostgreSQL, Redis, Umami, and both app services, then runs Alembic migrations before Uvicorn starts.

For a no-Docker Windows path that uses native PostgreSQL, Python, Node.js, npm, and PowerShell, see [Native Windows localhost development](./NATIVE_WINDOWS_LOCALHOST.md).

Local services:

- Backend API: `http://localhost:8000`
- Public frontend: `http://localhost:5173`
- Internal app: `http://localhost:8000/internal`
- Umami: `http://localhost:3000`
- Diagnostics panel: `http://localhost:8000/diagnostics_panel` when `DIAGNOSTICS_PANEL_ENABLED=true`

Internal development login defaults are configured in `docker-compose.yml`:

- Username: `admin`
- Password: `admin`

Useful Docker commands from the repository root:

```powershell
docker compose ps
docker compose logs backend
docker compose up -d backend
docker compose down
```

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

## Build and Deployment

The frontend production build is:

```bash
npm run build
```

The backend Dockerfile runs Alembic migrations and starts Uvicorn. The local Docker Compose stack is suitable for development, not a complete production deployment plan.

Production deployments should explicitly configure:

- secret management;
- database access and backups;
- Redis access;
- CORS origins;
- media storage;
- internal route exposure;
- analytics/diagnostics exposure;
- logging and monitoring;
- HTTPS and proxy headers.

For production analytics, use a production Umami instance and update:

```env
NEXT_PUBLIC_UMAMI_SCRIPT_URL=https://your-umami-domain.example.com/script.js
DIAGNOSTICS_DASHBOARD_URL=https://your-umami-domain.example.com/share/your-share-id
```

## Security Notes

- Protect internal routes with authentication.
- Keep diagnostics internal and root-admin-only.
- Protect write APIs and mutation routes.
- Never expose admin credentials.
- Never commit secrets.
- Replace development credentials before deployment.
- Use environment variables or secret management for production configuration.
- Do not make internal tools accessible from the public web without authentication.
- Review analytics configuration before production use, especially if Share URLs are publicly reachable.

## Documentation Links

- [Root README](../README.md)
- [Statements methodology](./STATEMENTS_METHODOLOGY.md)
- [Political programs methodology](./PPROGRAMS_METHODOLOGY.md)
- [Public methodology content](../frontend/src/content/methodology.bg.md)
