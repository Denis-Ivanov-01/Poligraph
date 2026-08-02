import pytest
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from app.main import app


@pytest.mark.anyio
async def test_internal_http_errors_render_internal_error_page():
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/internal/politicians/new",
            "headers": [],
            "query_string": b"",
            "server": ("testserver", 80),
            "scheme": "http",
            "client": ("testclient", 50000),
        }
    )

    response = await app.exception_handlers[StarletteHTTPException](request, StarletteHTTPException(405, "Method Not Allowed"))

    assert response.status_code == 405
    assert "text/html" in response.headers["content-type"]
    assert "Internal server error" in response.body.decode()
    assert "405: Method Not Allowed" in response.body.decode()
