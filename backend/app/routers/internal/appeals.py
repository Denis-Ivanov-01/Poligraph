from fastapi import APIRouter, Depends, Request

from app.dependencies import current_internal_user
from app.routers.internal.utils import render

router = APIRouter(prefix="/internal/appeals", tags=["internal-appeals"])


@router.get("")
def appeals(request: Request, user: dict = Depends(current_internal_user)):
    return render(request, "internal/appeals.html", {"user": user})
