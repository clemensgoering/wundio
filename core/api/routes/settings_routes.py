"""
Wundio – /api/settings routes

Two tiers:
  GET/PUT /api/settings/{key}          → SQLite DB (runtime state)
  GET/PUT /api/settings/env/{key}      → /etc/wundio/wundio.env (persistent config)
  GET     /api/settings/env            → all editable env keys + current values
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Any

from database import get_setting, set_setting, log_event

router = APIRouter(tags=["settings"])

ENV_FILE = Path("/etc/wundio/wundio.env")

# ── Which env keys are user-editable via the UI ────────────────────────────
# Format: key → { label, description, type, section, secret }
ENV_SCHEMA: dict[str, dict[str, Any]] = {
    # Spotify
    "SPOTIFY_DEVICE_NAME": {
        "label":       "Gerätename",
        "description": "Name der Wundio Box in der Spotify App",
        "type":        "text",
        "section":     "spotify",
        "secret":      False,
    },
    "SPOTIFY_BITRATE": {
        "label":       "Bitrate",
        "description": "Audioqualität: 96, 160 oder 320 kbit/s",
        "type":        "select",
        "options":     ["96", "160", "320"],
        "section":     "spotify",
        "secret":      False,
    },
    "SPOTIFY_CLIENT_ID": {
        "label":       "Client ID",
        "description": "Spotify Developer App – Client ID",
        "type":        "text",
        "section":     "spotify_api",
        "secret":      False,
    },
    "SPOTIFY_CLIENT_SECRET": {
        "label":       "Client Secret",
        "description": "Spotify Developer App – Client Secret",
        "type":        "password",
        "section":     "spotify_api",
        "secret":      True,
    },
    "SPOTIFY_REFRESH_TOKEN": {
        "label":       "Refresh Token",
        "description": "OAuth Refresh Token (einmalig per Autorisierung erzeugt)",
        "type":        "password",
        "section":     "spotify_api",
        "secret":      True,
    },
    # Display
    "DISPLAY_I2C_ADDRESS": {
        "label":       "OLED I2C Adresse",
        "description": "Standard: 0x3C – einige Displays nutzen 0x3D",
        "type":        "text",
        "section":     "hardware",
        "secret":      False,
    },
    # Hotspot
    "HOTSPOT_SSID": {
        "label":       "Hotspot SSID",
        "description": "WLAN-Name für den Ersteinrichtungs-Hotspot",
        "type":        "text",
        "section":     "hotspot",
        "secret":      False,
    },
    "HOTSPOT_PASSWORD": {
        "label":       "Hotspot Passwort",
        "description": "Mindestens 8 Zeichen",
        "type":        "password",
        "section":     "hotspot",
        "secret":      True,
    },
    # GPIO (advanced)
    "RFID_RST_PIN": {
        "label":       "RFID RST Pin (BCM)",
        "description": "Standard: 25",
        "type":        "text",
        "section":     "hardware",
        "secret":      False,
    },
    "BUTTON_PLAY_PAUSE_PIN": {
        "label":       "Button Play/Pause (BCM)",
        "description": "Standard: 17",
        "type":        "text",
        "section":     "hardware",
        "secret":      False,
    },
}


def _read_env() -> dict[str, str]:
    """Parse /etc/wundio/wundio.env into a key→value dict."""
    result: dict[str, str] = {}
    if not ENV_FILE.exists():
        return result
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, _, v = line.partition("=")
            result[k.strip()] = v.strip()
    return result


def _write_env_key(key: str, value: str) -> None:
    """Update or insert a single key in the env file."""
    if not ENV_FILE.exists():
        raise HTTPException(status_code=500, detail=f"{ENV_FILE} not found")

    lines = ENV_FILE.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"{key}={value}")

    ENV_FILE.write_text("\n".join(new_lines) + "\n")


# ── DB settings ────────────────────────────────────────────────────────────

class SettingWrite(BaseModel):
    value: str


@router.get("/{key}")
async def read_setting(key: str):
    if key == "env":
        raise HTTPException(status_code=400, detail="Use /api/settings/env")
    return {"key": key, "value": get_setting(key)}


@router.put("/{key}")
async def write_setting(key: str, data: SettingWrite):
    if key == "env":
        raise HTTPException(status_code=400, detail="Use /api/settings/env/{key}")
    set_setting(key, data.value)
    log_event("settings", f"Einstellung gespeichert: {key}")
    return {"ok": True}


# ── Env settings ────────────────────────────────────────────────────────────

@router.get("/env/schema")
async def env_schema():
    """Return the schema of all editable env keys."""
    return ENV_SCHEMA


@router.get("/env/all")
async def env_all():
    """Return all editable env keys with current values (secrets masked)."""
    current = _read_env()
    result = []
    for key, meta in ENV_SCHEMA.items():
        raw_value = current.get(key, "")
        result.append({
            "key":         key,
            "value":       "••••••••" if (meta["secret"] and raw_value) else raw_value,
            "has_value":   bool(raw_value),
            **meta,
        })
    return result


@router.get("/env/{key}")
async def read_env_setting(key: str):
    key = key.upper()
    if key not in ENV_SCHEMA:
        raise HTTPException(status_code=404, detail=f"Key '{key}' is not user-editable")
    current = _read_env()
    raw = current.get(key, "")
    meta = ENV_SCHEMA[key]
    return {
        "key":       key,
        "value":     "••••••••" if (meta["secret"] and raw) else raw,
        "has_value": bool(raw),
        **meta,
    }


class EnvWrite(BaseModel):
    value: str


@router.put("/env/{key}")
async def write_env_setting(key: str, data: EnvWrite):
    key = key.upper()
    if key not in ENV_SCHEMA:
        raise HTTPException(status_code=404, detail=f"Key '{key}' is not user-editable")

    try:
        _write_env_key(key, data.value)
        # Mask secrets in log
        display_val = "***" if ENV_SCHEMA[key]["secret"] else data.value
        log_event("settings", f"Konfiguration aktualisiert: {key} = {display_val}")
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=f"Keine Schreibrechte auf {ENV_FILE}. "
                   "Bitte 'chown root:wundio /etc/wundio/wundio.env && chmod 660 /etc/wundio/wundio.env' ausführen."
        )
    return {"ok": True, "restart_required": True}