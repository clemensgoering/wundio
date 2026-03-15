"""
Wundio – /api/settings routes
"""
from fastapi import APIRouter
from pydantic import BaseModel

from database import get_setting, set_setting, log_event

router = APIRouter(tags=["settings"])


class SettingWrite(BaseModel):
    value: str


@router.get("/{key}")
async def read_setting(key: str):
    return {"key": key, "value": get_setting(key)}


@router.put("/{key}")
async def write_setting(key: str, data: SettingWrite):
    set_setting(key, data.value)
    log_event("settings", f"Setting updated: {key}")
    return {"ok": True}
