from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.models.revision import EntityRevision


def _json_value(value: Any) -> Any:
    if isinstance(value, (UUID, date, datetime)):
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def create_entity_revision(db: Session, entity: Any, user: dict | None, change_note: str) -> EntityRevision:
    state = inspect(entity)
    entity_type = state.mapper.local_table.name
    entity_id = entity.id
    data = {attribute.key: _json_value(getattr(entity, attribute.key)) for attribute in state.mapper.column_attrs}
    next_revision = (
        db.scalar(
            select(func.coalesce(func.max(EntityRevision.revision_number), 0) + 1).where(
                EntityRevision.entity_type == entity_type,
                EntityRevision.entity_id == entity_id,
            )
        )
        or 1
    )
    moderator = user.get("moderator") if user else None
    revision = EntityRevision(
        entity_type=entity_type,
        entity_id=entity_id,
        revision_number=next_revision,
        data_json=data,
        created_by_user_id=moderator.id if moderator else None,
        change_note=change_note,
    )
    db.add(revision)
    return revision
