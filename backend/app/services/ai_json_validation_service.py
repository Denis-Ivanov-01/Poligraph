import json

from pydantic import ValidationError

from app.schemas.ai_analysis import AiAnalysisInput


def _json_error_context(raw_json: str, position: int, radius: int = 120) -> str:
    start = max(position - radius, 0)
    end = min(position + radius, len(raw_json))
    excerpt = raw_json[start:end].replace("\n", "\\n")
    pointer = " " * max(position - start, 0) + "^"
    return f"{excerpt}\n{pointer}"


def validate_ai_json(raw_json: str) -> AiAnalysisInput:
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        context = _json_error_context(raw_json, exc.pos)
        raise ValueError(f"Invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}\n{context}") from exc
    try:
        return AiAnalysisInput.model_validate(data)
    except ValidationError as exc:
        raise ValueError(exc.json()) from exc
