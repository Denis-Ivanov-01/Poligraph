from app.main import app
from app.resources import methodology_text


def test_methodology_markdown_endpoint_serves_statements_page():
    content = methodology_text("statements", "bg-BG")

    assert content.lstrip("\ufeff").startswith("# Пълна методологична обосновка")


def test_methodology_markdown_endpoint_is_registered():
    route_paths = set(app.openapi()["paths"])

    assert "/api/resources/{locale}/methodology/{page}" in route_paths
