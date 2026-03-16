"""
Wundio – /api/settings routes

Two tiers:
  GET/PUT /api/settings/{key}          → SQLite DB (runtime state)
  GET/PUT /api/settings/env/{key}      → /etc/wundio/wundio.env (persistent config)
  GET     /api/settings/env/all        → all editable env keys + current values
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pathlib import Path
from typing import Any

from database import get_setting, set_setting, log_event

router = APIRouter(tags=["settings"])

ENV_FILE = Path("/etc/wundio/wundio.env")

ENV_SCHEMA: dict[str, dict[str, Any]] = {
    # ── Spotify ────────────────────────────────────────────────────────────
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
    # ── Spotify Web API (REFRESH_TOKEN is set via OAuth, not manually) ─────
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
    # SPOTIFY_REFRESH_TOKEN is intentionally excluded from the UI schema.
    # It is written automatically by the OAuth callback (/api/spotify/callback).
    # ── Display ────────────────────────────────────────────────────────────
    "DISPLAY_TYPE": {
        "label":       "Display-Typ",
        "description": "Art des angeschlossenen Displays. 'none' deaktiviert die Anzeige.",
        "type":        "select",
        "options":     ["none", "oled", "tft"],
        "section":     "display",
        "secret":      False,
    },
    "DISPLAY_MODEL": {
        "label":       "Display-Modell",
        "description": "OLED: ssd1306 oder sh1106 · TFT: st7735 (128×160) oder ili9341 (240×320)",
        "type":        "select",
        "options":     ["ssd1306", "sh1106", "st7735", "ili9341"],
        "section":     "display",
        "secret":      False,
    },
    "DISPLAY_I2C_ADDRESS": {
        "label":       "OLED I2C Adresse",
        "description": "Standard: 0x3C – einige Displays nutzen 0x3D",
        "type":        "text",
        "section":     "display",
        "secret":      False,
    },
    "DISPLAY_WIDTH": {
        "label":       "Breite (px)",
        "description": "OLED: 128 · ST7735: 128 · ILI9341: 240",
        "type":        "text",
        "section":     "display",
        "secret":      False,
    },
    "DISPLAY_HEIGHT": {
        "label":       "Höhe (px)",
        "description": "OLED: 64 · ST7735: 160 · ILI9341: 320",
        "type":        "text",
        "section":     "display",
        "secret":      False,
    },
    # ── RFID ──────────────────────────────────────────────────────────────
    "RFID_TYPE": {
        "label":       "RFID-Reader Typ",
        "description": "rc522 = SPI (Standard) · pn532 = I2C (NFC-kompatibel)",
        "type":        "select",
        "options":     ["rc522", "pn532"],
        "section":     "rfid",
        "secret":      False,
    },
    # ── Audio ──────────────────────────────────────────────────────────────
    "AUDIO_TYPE": {
        "label":       "Audio-Ausgabe",
        "description": "usb = USB-Soundkarte · i2s_max98357 = DAC · hifiberry = HiFiBerry HAT",
        "type":        "select",
        "options":     ["usb", "i2s_max98357", "hifiberry"],
        "section":     "audio",
        "secret":      False,
    },
    # ── Hotspot ────────────────────────────────────────────────────────────
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
    # ── GPIO / Hardware (Advanced) ─────────────────────────────────────────
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
    "DISPLAY_DC_PIN": {
        "label":       "TFT DC-Pin (BCM)",
        "description": "Nur TFT: Data/Command-Pin. Standard: 16",
        "type":        "text",
        "section":     "hardware",
        "secret":      False,
    },
    "DISPLAY_RST_PIN": {
        "label":       "TFT RST-Pin (BCM)",
        "description": "Nur TFT: Reset-Pin. Standard: 20",
        "type":        "text",
        "section":     "hardware",
        "secret":      False,
    },
    "DISPLAY_SPI_DEV": {
        "label":       "TFT SPI CE (0 oder 1)",
        "description": "Nur TFT: CE1 freilassen wenn RC522 auf CE0 läuft. Standard: 1",
        "type":        "select",
        "options":     ["0", "1"],
        "section":     "hardware",
        "secret":      False,
    },
}

# Keys that require a service restart to take effect
_RESTART_KEYS = {
    "SPOTIFY_DEVICE_NAME", "SPOTIFY_BITRATE",
    "DISPLAY_TYPE", "DISPLAY_MODEL", "DISPLAY_I2C_ADDRESS",
    "DISPLAY_WIDTH", "DISPLAY_HEIGHT", "DISPLAY_DC_PIN",
    "DISPLAY_RST_PIN", "DISPLAY_SPI_DEV",
    "RFID_TYPE", "RFID_RST_PIN",
    "AUDIO_TYPE",
    "BUTTON_PLAY_PAUSE_PIN",
}


def _read_env() -> dict[str, str]:
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


# ── Env routes (must come before /{key}) ──────────────────────────────────

@router.get("/env/schema")
async def env_schema():
    return ENV_SCHEMA


@router.get("/env/all")
async def env_all():
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
        display_val = "***" if ENV_SCHEMA[key]["secret"] else data.value
        log_event("settings", f"Konfiguration aktualisiert: {key} = {display_val}")
    except PermissionError:
        raise HTTPException(
            status_code=403,
            detail=(
                f"Keine Schreibrechte auf {ENV_FILE}. "
                "Bitte ausführen: chown root:wundio /etc/wundio/wundio.env && chmod 660 /etc/wundio/wundio.env"
            )
        )
    return {"ok": True, "restart_required": key in _RESTART_KEYS}


# ── DB settings ────────────────────────────────────────────────────────────

class SettingWrite(BaseModel):
    value: str


@router.get("/{key}")
async def read_setting(key: str):
    return {"key": key, "value": get_setting(key)}


@router.put("/{key}")
async def write_setting(key: str, data: SettingWrite):
    set_setting(key, data.value)
    log_event("settings", f"Einstellung gespeichert: {key}")
    return {"ok": True}