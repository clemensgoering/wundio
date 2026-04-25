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
    local_ip: str
    hardware: dict
    features: dict


def _get_local_ip() -> str:
    """Get wlan0 IP address for displaying in UI."""
    import subprocess
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=2
        )
        for line in result.stdout.splitlines():
            if "inet " in line:
                return line.split()[1].split('/')[0]
    except Exception:
        pass
    return "192.168.1.XXX"


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
        local_ip=_get_local_ip(),
        hardware={
            "model": profile_dict["model"],
            "ram_mb": profile_dict["ram_mb"],
            "pi_generation": profile_dict["pi_generation"],
        },
        features=profile_dict["features"],
    )


@router.get("/health")
async def health():
    return {"status": "ok", "message": "Wundio API running"}


@router.get("/events")
async def get_events(limit: int = 100, source: str = ""):
    """Return recent system events for the activity log page."""
    from database import get_engine, SystemEvent
    from sqlmodel import Session, select
    with Session(get_engine()) as session:
        q = select(SystemEvent).order_by(SystemEvent.id.desc())
        if source:
            q = q.where(SystemEvent.source == source)
        q = q.limit(min(limit, 500))
        events = session.exec(q).all()
    return [
        {
            "id":        e.id,
            "level":     e.level   or "INFO",
            "source":    e.source  or "system",
            "message":   e.message or "",
            "timestamp": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.post("/complete-setup")
async def complete_setup():
    from database import set_setting
    set_setting("setup_complete", "true")
    log_event("system", "Einrichtung abgeschlossen")
    return {"ok": True}


@router.post("/restart")
async def restart_service():
    """Restart wundio-core service to apply config changes."""
    import subprocess
    import asyncio
    log_event("system", "Neustart des Dienstes angefordert")
    # Delayed restart so the response can be sent first
    async def _restart():
        await asyncio.sleep(1)
        subprocess.Popen(["systemctl", "restart", "wundio-core"])
    asyncio.create_task(_restart())
    return {"ok": True, "message": "Wundio wird neu gestartet..."}
