import json
from functools import lru_cache
from pathlib import Path
from typing import Any


RESOURCE_PATH = Path(__file__).with_name("resources.json")


@lru_cache
def resources() -> dict[str, Any]:
    return json.loads(RESOURCE_PATH.read_text(encoding="utf-8"))


def resource_text(path: str, default: str = "") -> str:
    value: Any = resources()
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            return default
        value = value[key]
    return value if isinstance(value, str) else default
