from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import RedirectResponse

from app.config import get_settings
from app.routers.internal.utils import render
from app.routers.internal import ai_workflow, appeals, audit_logs, auth, diagnostics, home, moderators, parties as internal_parties
from app.routers.internal import politicians as internal_politicians
from app.routers.internal import programs as internal_programs
from app.routers.internal import statements as internal_statements
from app.routers.public import dashboard, parties, politicians, programs, resources, search, statements


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
    app.include_router(resources.router, prefix="/api")

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

    @app.exception_handler(StarletteHTTPException)
    async def internal_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if request.url.path.startswith("/internal"):
            if exc.status_code in {301, 302, 303, 307, 308} and exc.headers and exc.headers.get("Location"):
                return RedirectResponse(exc.headers["Location"], status_code=exc.status_code)
            return render(
                request,
                "internal/error.html",
                {"error": f"{exc.status_code}: {exc.detail}"},
                status_code=exc.status_code,
            )
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(Exception)
    async def internal_exception_handler(request: Request, exc: Exception):
        if request.url.path.startswith("/internal"):
            return render(
                request,
                "internal/error.html",
                {"error": f"{type(exc).__name__}: {exc}"},
                status_code=500,
            )
        raise exc

    return app


app = create_app()
