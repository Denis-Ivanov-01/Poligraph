from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import get_settings


async def save_upload(file: UploadFile) -> tuple[str, str | None]:
    root = Path(get_settings().media_storage_path)
    root.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "").suffix
    name = f"{uuid4()}{suffix}"
    target = root / name
    target.write_bytes(await file.read())
    return str(target), file.filename
