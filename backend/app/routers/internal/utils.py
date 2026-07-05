from fastapi import Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

from app.config import get_settings
from app.security import ensure_csrf_token, get_session, set_session

templates = Jinja2Templates(directory="app/templates")


def render(request: Request, template_name: str, context: dict | None = None, status_code: int = 200) -> Response:
    context = context or {}
    csrf_token = ensure_csrf_token(request)
    settings = get_settings()
    response = templates.TemplateResponse(
        request,
        template_name,
        {
            **context,
            "csrf_token": csrf_token,
            "diagnostics_panel_enabled": settings.diagnostics_panel_enabled,
            "diagnostics_panel_path": settings.diagnostics_route_path,
            "session": get_session(request),
        },
        status_code=status_code,
    )
    if getattr(request.state, "pending_csrf_token", None):
        session = get_session(request)
        session["csrf_token"] = request.state.pending_csrf_token
        set_session(response, session)
    return response
