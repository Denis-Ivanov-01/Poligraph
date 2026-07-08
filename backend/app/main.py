from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.internal import ai_workflow, appeals, audit_logs, auth, diagnostics, home, moderators, parties as internal_parties
from app.routers.internal import politicians as internal_politicians
from app.routers.internal import programs as internal_programs
from app.routers.internal import statements as internal_statements
from app.routers.public import dashboard, parties, politicians, programs, search, statements


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Political AI Filter API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory="app/static"), name="static")

    app.include_router(parties.router, prefix="/api")
    app.include_router(politicians.router, prefix="/api")
    app.include_router(statements.router, prefix="/api")
    app.include_router(programs.router, prefix="/api")
    app.include_router(dashboard.router, prefix="/api")
    app.include_router(search.router, prefix="/api")

    app.include_router(auth.router)
    app.include_router(home.router)
    app.include_router(internal_parties.router)
    app.include_router(internal_politicians.router)
    app.include_router(internal_statements.router)
    app.include_router(internal_programs.router)
    app.include_router(ai_workflow.router)
    app.include_router(moderators.router)
    app.include_router(audit_logs.router)
    app.include_router(appeals.router)
    app.include_router(diagnostics.router)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app


app = create_app()
