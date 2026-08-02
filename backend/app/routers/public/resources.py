from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.resources import DEFAULT_LOCALE, methodology_text, public_resources

router = APIRouter(prefix="/resources", tags=["public-resources"])


@router.get("/{locale}/resources")
def resources_by_locale(locale: str):
    try:
        return public_resources(locale)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Locale not found") from None


@router.get("/{locale}/methodology/{page}", response_class=PlainTextResponse)
def methodology_by_locale(locale: str, page: str):
    try:
        return methodology_text(page, locale)
    except FileNotFoundError:
        detail = "Locale not found" if locale != DEFAULT_LOCALE else "Methodology page not found"
        raise HTTPException(status_code=404, detail=detail) from None
