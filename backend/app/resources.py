import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_LOCALE = "bg-BG"
RESOURCE_ROOT_CANDIDATES = (
    Path.cwd() / "resources",
    Path.cwd().parent / "resources",
    Path(__file__).resolve().parents[2] / "resources",
    Path("/resources"),
)
BACKEND_RESOURCE_NAME = "backend.json"
PUBLIC_RESOURCE_NAME = "resources.json"
METHODOLOGY_PAGES = {
    "statements": "statements-methodology.md",
    "programs": "programs-methodology.md",
    "controversial-topics": "controversial-topics-methodology.md",
}


def resource_root() -> Path:
    for path in RESOURCE_ROOT_CANDIDATES:
        if path.exists():
            return path
    return RESOURCE_ROOT_CANDIDATES[0]


def _locale_dir(locale: str = DEFAULT_LOCALE) -> Path:
    if locale != DEFAULT_LOCALE:
        raise FileNotFoundError(locale)
    return resource_root() / locale


@lru_cache
def resources(locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
    return json.loads((_locale_dir(locale) / BACKEND_RESOURCE_NAME).read_text(encoding="utf-8"))


@lru_cache
def public_resources(locale: str = DEFAULT_LOCALE) -> dict[str, Any]:
    return json.loads((_locale_dir(locale) / PUBLIC_RESOURCE_NAME).read_text(encoding="utf-8"))


@lru_cache
def methodology_text(page: str, locale: str = DEFAULT_LOCALE) -> str:
    filename = METHODOLOGY_PAGES.get(page)
    if not filename:
        raise FileNotFoundError(page)
    return (_locale_dir(locale) / filename).read_text(encoding="utf-8")


def resource_text(path: str, default: str = "") -> str:
    value: Any = resources()
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value if isinstance(value, str) else default
