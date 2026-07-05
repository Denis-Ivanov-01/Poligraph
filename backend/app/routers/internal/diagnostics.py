from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Request

from app.config import get_settings
from app.dependencies import root_admin_required
from app.routers.internal.utils import render

router = APIRouter(tags=["internal-diagnostics"])


def _safe_dashboard_url(value: str) -> str | None:
    parsed = urlparse(value.strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return value.strip()


def diagnostics_panel(request: Request, user: dict = Depends(root_admin_required)):
    settings = get_settings()
    dashboard_url = _safe_dashboard_url(settings.diagnostics_dashboard_url)
    return render(
        request,
        "internal/diagnostics_panel.html",
        {
            "user": user,
            "diagnostics_enabled": settings.diagnostics_panel_enabled,
            "dashboard_url": dashboard_url,
            "dashboard_url_configured": bool(settings.diagnostics_dashboard_url.strip()),
            "diagnostics_path": settings.diagnostics_route_path,
        },
        status_code=200 if settings.diagnostics_panel_enabled else 404,
    )


router.add_api_route("/diagnostics_panel", diagnostics_panel, methods=["GET"])

configured_path = get_settings().diagnostics_route_path
if configured_path != "/diagnostics_panel":
    router.add_api_route(configured_path, diagnostics_panel, methods=["GET"])
