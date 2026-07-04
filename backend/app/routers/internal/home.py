from fastapi import APIRouter, Depends, Request

from app.dependencies import current_internal_user
from app.routers.internal.utils import render

router = APIRouter(prefix="/internal", tags=["internal-home"])


@router.get("")
def internal_home(request: Request, user: dict = Depends(current_internal_user)):
    return render(request, "internal/index.html", {"user": user})
