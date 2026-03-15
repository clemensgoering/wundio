"""
Wundio – Central Configuration
All settings are resolved from environment variables with sensible defaults.
Hardware-dependent settings are layered on top via the HardwareProfile.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


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
    static_dir: str = "/opt/wundio/web/dist"

    # ── Hardware Pins (BCM numbering) ─────────────────────────────────
    # RFID RC522 via SPI
    rfid_rst_pin: int = 25
    rfid_spi_bus: int = 0
    rfid_spi_dev: int = 0

    # I2C OLED (SSD1306 / SH1106 compatible)
    display_i2c_address: int = 0x3C     # default SSD1306; 0x3D for some variants
    display_i2c_bus: int = 1
    display_width: int = 128
    display_height: int = 64

    # Buttons (BCM pins – adjust to wiring)
    button_play_pause_pin: int = 17
    button_next_pin: int = 27
    button_prev_pin: int = 22
    button_vol_up_pin: int = 23
    button_vol_down_pin: int = 24

    # ── Spotify / librespot ───────────────────────────────────────────
    spotify_device_name: str = "Wundio"
    spotify_bitrate: int = 160          # 96 | 160 | 320

    # ── WiFi Hotspot (first-run AP) ───────────────────────────────────
    hotspot_ssid: str = "Wundio-Setup"
    hotspot_password: str = "wundio123"
    hotspot_ip: str = "192.168.50.1"

    # ── AI / LLM ──────────────────────────────────────────────────────
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"           # default for Pi 5 8GB
    whisper_model: str = "tiny"                  # tiny|base|small – Pi 3: tiny only
    tts_voice: str = "de_DE-thorsten-medium"     # Piper voice

    model_config = {
        "env_file": "/etc/wundio/wundio.env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
