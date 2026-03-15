"""
Wundio – Central Configuration
All settings are resolved from environment variables with sensible defaults.
Hardware-dependent settings are layered on top via the HardwareProfile.
"""

from functools import lru_cache
from typing import Annotated
from pydantic import field_validator
from pydantic_settings import BaseSettings


def _parse_int(v: object) -> int:
    """Accept decimal (60) and hex strings (0x3C) for integer fields."""
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        return int(v, 0)   # int('0x3C', 0) → 60, int('60', 0) → 60
    raise ValueError(f"Cannot parse {v!r} as integer")


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────
    app_name: str = "Wundio"
    app_version: str = "0.1.0"
    debug: bool = False

    # ── Database ──────────────────────────────────────────────────────
    db_path: str = "/var/lib/wundio/wundio.db"

    # ── Web Server ────────────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8000
    static_dir: str = "/opt/wundio/core/static/web"

    # ── Hardware Pins (BCM numbering) ─────────────────────────────────
    rfid_rst_pin: int = 25
    rfid_spi_bus: int = 0
    rfid_spi_dev: int = 0

    # I2C OLED – accepts hex (0x3C) or decimal (60) from env file
    display_i2c_address: int = 0x3C
    display_i2c_bus: int = 1
    display_width: int = 128
    display_height: int = 64

    # Buttons (BCM pins)
    button_play_pause_pin: int = 17
    button_next_pin: int = 27
    button_prev_pin: int = 22
    button_vol_up_pin: int = 23
    button_vol_down_pin: int = 24

    # ── Spotify / librespot ───────────────────────────────────────────
    spotify_device_name: str = "Wundio"
    spotify_bitrate: int = 160

    # ── WiFi Hotspot (first-run AP) ───────────────────────────────────
    hotspot_ssid: str = "Wundio-Setup"
    hotspot_password: str = "wundio123"
    hotspot_ip: str = "192.168.50.1"

    # ── AI / LLM ──────────────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    whisper_model: str = "tiny"
    tts_voice: str = "de_DE-thorsten-medium"

    # ── Validator: parse hex strings for all int fields ───────────────
    @field_validator(
        "display_i2c_address",
        "display_i2c_bus",
        "display_width",
        "display_height",
        "rfid_rst_pin",
        "rfid_spi_bus",
        "rfid_spi_dev",
        "button_play_pause_pin",
        "button_next_pin",
        "button_prev_pin",
        "button_vol_up_pin",
        "button_vol_down_pin",
        "port",
        mode="before",
    )
    @classmethod
    def parse_int_or_hex(cls, v: object) -> int:
        return _parse_int(v)

    model_config = {
        "env_file": "/etc/wundio/wundio.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()