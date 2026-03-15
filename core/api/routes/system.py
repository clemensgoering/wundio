"""
Wundio – /api/system routes
"""
from fastapi import APIRouter
from pydantic import BaseModel

from config import get_settings
from database import get_setting, log_event
from services.hardware import get_profile

router = APIRouter(tags=["system"])


class SystemStatus(BaseModel):
    app_name: str
    version: str
    setup_complete: bool
    hotspot_active: bool
    hardware: dict
    features: dict


@router.get("/status", response_model=SystemStatus)
async def get_status():
    cfg = get_settings()
    hw = get_profile()
    profile_dict = hw.to_dict()
    return SystemStatus(
        app_name=cfg.app_name,
        version=cfg.app_version,
        setup_complete=get_setting("setup_complete") == "true",
        hotspot_active=get_setting("hotspot_active") == "true",
        hardware={
            "model": profile_dict["model"],
            "ram_mb": profile_dict["ram_mb"],
            "pi_generation": profile_dict["pi_generation"],
        },
        features=profile_dict["features"],
    )


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/complete-setup")
async def complete_setup():
    from database import set_setting
    set_setting("setup_complete", "true")
    log_event("system", "Setup marked as complete")
    return {"ok": True}
