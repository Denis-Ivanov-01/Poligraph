# Backend

FastAPI backend for the Political AI Filter MVP.

## Commands

```bash
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The internal app is mounted under `/internal`; the public API is mounted under `/api`.
