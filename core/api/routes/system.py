"""
Wundio – /api/system routes

Endpoints:
  GET  /api/system/status        – app info, hardware profile, feature flags
  GET  /api/system/health        – liveness probe
  GET  /api/system/events        – activity log (paginated)
  POST /api/system/complete-setup – mark first-run setup done
  POST /api/system/restart       – restart the wundio-core systemd service

Note on /restart vs /api/system/actions/restart-service/run:
  /restart returns a plain JSON response immediately (fire-and-forget).
  It is intended for the Settings UI "Neu starten" button where the client
  does not need a live log stream. Internally it delegates to the same
  whitelist entry in system_actions so the subprocess logic lives in one place.
  The /actions SSE endpoint remains available for the admin panel.
"""
import asyncio
import logging
import subprocess

from fastapi import APIRouter
from pydantic import BaseModel

from config import get_settings
from database import get_setting, log_event
from services.hardware import get_profile

router = APIRouter(tags=["system"])
logger = logging.getLogger(__name__)


class SystemStatus(BaseModel):
    app_name: str
    version: str
    setup_complete: bool
    hotspot_active: bool
    local_ip: str
    hardware: dict
    features: dict


def _get_local_ip() -> str:
    """Return the wlan0 IPv4 address, or a placeholder when unavailable."""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=2,
        )
        for line in result.stdout.splitlines():
            if "inet " in line:
                return line.split()[1].split("/")[0]
    except Exception:
        pass
    return "192.168.1.XXX"


@router.get("/status", response_model=SystemStatus)
async def get_status():
    cfg          = get_settings()
    hw           = get_profile()
    profile_dict = hw.to_dict()
    return SystemStatus(
        app_name       = cfg.app_name,
        version        = cfg.app_version,
        setup_complete = get_setting("setup_complete") == "true",
        hotspot_active = get_setting("hotspot_active") == "true",
        local_ip       = _get_local_ip(),
        hardware       = {
            "model":         profile_dict["model"],
            "ram_mb":        profile_dict["ram_mb"],
            "pi_generation": profile_dict["pi_generation"],
        },
        features = profile_dict["features"],
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
            "level":     e.level    or "INFO",
            "source":    e.source   or "system",
            "message":   e.message  or "",
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
    """Restart the wundio-core systemd service (fire-and-forget).

    Returns immediately with a JSON acknowledgement. The restart is delayed by
    one second so the HTTP response can be delivered before the process exits.

    For a live log stream of the restart, use:
      POST /api/system/actions/restart-service/run
    """
    log_event("system", "Neustart des Dienstes angefordert")

    async def _restart() -> None:
        await asyncio.sleep(1)
        subprocess.Popen(["systemctl", "restart", "wundio-core"])

    asyncio.create_task(_restart())
    return {"ok": True, "message": "Wundio wird neu gestartet..."}