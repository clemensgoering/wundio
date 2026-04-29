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


@router.get("/services")
async def get_services_status():
    """
    Returns runtime status of system services and Spotify device visibility.
    """
    import subprocess
    import json as _json
    import urllib.request
    import base64
    import urllib.parse

    def _systemctl_status(service: str) -> dict:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", service],
                capture_output=True, text=True, timeout=3,
            )
            active = r.stdout.strip() == "active"
            since = ""
            if active:
                r2 = subprocess.run(
                    ["systemctl", "show", service, "--property=ActiveEnterTimestamp"],
                    capture_output=True, text=True, timeout=3,
                )
                for line in r2.stdout.splitlines():
                    if line.startswith("ActiveEnterTimestamp="):
                        since = line.split("=", 1)[1].strip()
                        break
            return {"active": active, "since": since}
        except Exception:
            return {"active": False, "since": ""}

    def _librespot_process_status() -> dict:
        """
        librespot runs as a child process of wundio-core, not a systemd unit.
        Detect via pgrep instead of systemctl.
        """
        try:
            r = subprocess.run(
                ["pgrep", "-x", "librespot"],
                capture_output=True, timeout=3,
            )
            return {"active": r.returncode == 0, "since": "", "mode": "process"}
        except Exception:
            return {"active": False, "since": "", "mode": "process"}

    services = {
        "wundio-core":      _systemctl_status("wundio-core"),
        "wundio-librespot": _librespot_process_status(),
    }

    # Spotify device visibility
    spotify_device: dict = {"found": False, "name": "", "is_active": False, "error": ""}
    try:
        from config import get_settings
        from services.spotify import get_spotify_service

        cfg = get_settings()
        client_id     = getattr(cfg, "spotify_client_id",     "")
        client_secret = getattr(cfg, "spotify_client_secret", "")
        refresh_token = getattr(cfg, "spotify_refresh_token", "")

        if all([client_id, client_secret, refresh_token]):
            creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            token_req = urllib.request.Request(
                "https://accounts.spotify.com/api/token",
                data=urllib.parse.urlencode({
                    "grant_type":    "refresh_token",
                    "refresh_token": refresh_token,
                }).encode(),
                headers={
                    "Authorization": f"Basic {creds}",
                    "Content-Type":  "application/x-www-form-urlencoded",
                },
            )
            with urllib.request.urlopen(token_req, timeout=5) as resp:
                access_token = _json.loads(resp.read()).get("access_token", "")

            if access_token:
                svc = get_spotify_service()
                device_name = svc._device_name.lower()
                devices_req = urllib.request.Request(
                    "https://api.spotify.com/v1/me/player/devices",
                    headers={"Authorization": f"Bearer {access_token}"},
                )
                with urllib.request.urlopen(devices_req, timeout=5) as resp:
                    all_devices = _json.loads(resp.read()).get("devices", [])

                for d in all_devices:
                    if device_name in d.get("name", "").lower():
                        spotify_device = {
                            "found":     True,
                            "name":      d["name"],
                            "is_active": d.get("is_active", False),
                            "error":     "",
                        }
                        break

                if not spotify_device["found"]:
                    spotify_device["error"] = (
                        f"Gerät '{svc._device_name}' nicht sichtbar. "
                        "Wundio startet im Hintergrund – bitte kurz warten oder Service neu starten."
                    )
        else:
            spotify_device["error"] = "Spotify Web API nicht konfiguriert"

    except Exception as exc:
        spotify_device["error"] = str(exc)

    return {
        "services":       services,
        "spotify_device": spotify_device,
    }