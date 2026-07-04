from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.public.utils import statement_list_payload
from app.services.dashboard_service import dashboard_data

router = APIRouter(prefix="/dashboard", tags=["public-dashboard"])


@router.get("")
def dashboard(db: Session = Depends(get_db)):
    data = dashboard_data(db)
    data["latest_statements"] = [statement_list_payload(item) for item in data["latest_statements"]]
    return data
