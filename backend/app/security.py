import secrets
from typing import Any

from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, URLSafeSerializer
from passlib.context import CryptContext

from app.config import get_settings


pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    if password_hash.startswith("plain:"):
        return plain_password == password_hash.removeprefix("plain:")
    try:
        return pwd_context.verify(plain_password, password_hash)
    except Exception:
        return False


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def _serializer() -> URLSafeSerializer:
    settings = get_settings()
    return URLSafeSerializer(settings.app_secret_key, salt="politic-bs-session")


def get_session(request: Request) -> dict[str, Any]:
    settings = get_settings()
    raw = request.cookies.get(settings.session_cookie_name)
    if not raw:
        return {}
    try:
        data = _serializer().loads(raw)
    except BadSignature:
        return {}
    return data if isinstance(data, dict) else {}


def set_session(response: Response, data: dict[str, Any]) -> None:
    settings = get_settings()
    response.set_cookie(
        settings.session_cookie_name,
        _serializer().dumps(data),
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(get_settings().session_cookie_name)


def ensure_csrf_token(request: Request) -> str:
    session = get_session(request)
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.state.pending_csrf_token = token
    return token


def validate_csrf(request: Request, token: str) -> None:
    if not token or token != get_session(request).get("csrf_token"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")
