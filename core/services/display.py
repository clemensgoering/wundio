"""
Wundio – OLED Display Service (I2C, SSD1306/SH1106 128x64)
Handles system feedback, user greeting, playback status.
Falls back to console logging when hardware is absent.
"""

import logging
import asyncio
from typing import Optional
from enum import Enum

logger = logging.getLogger(__name__)


class DisplayMode(str, Enum):
    BOOT       = "boot"
    IDLE       = "idle"
    PLAYING    = "playing"
    USER_LOGIN = "user_login"
    SETUP      = "setup"
    ERROR      = "error"


class OledDisplay:
    """
    Wraps luma.oled for SSD1306 I2C.
    All methods are safe to call even without physical hardware.
    """

    def __init__(self, i2c_address: int = 0x3C, i2c_bus: int = 1,
                 width: int = 128, height: int = 64):
        self._address = i2c_address
        self._bus = i2c_bus
        self._width = width
        self._height = height
        self._device = None
        self._available = False
        self._current_mode = DisplayMode.BOOT

    def setup(self) -> bool:
        """Initialize display. Returns True if hardware found."""
        try:
            from luma.core.interface.serial import i2c
            from luma.oled.device import ssd1306
            serial = i2c(port=self._bus, address=self._address)
            self._device = ssd1306(serial, width=self._width, height=self._height)
            self._available = True
            logger.info(f"OLED display initialized at I2C {hex(self._address)}")
            return True
        except Exception as e:
            logger.warning(f"OLED not available: {e} – using console fallback")
            self._available = False
            return False

    def _draw(self, fn) -> None:
        """Run a PIL draw function on the display."""
        if not self._available or self._device is None:
            return
        try:
            from luma.core.render import canvas
            with canvas(self._device) as draw:
                fn(draw)
        except Exception as e:
            logger.error(f"Display draw error: {e}")

    def _font(self, size: int = 10):
        try:
            from PIL import ImageFont
            # Use a basic bitmap font – no TTF required
            return ImageFont.load_default()
        except Exception:
            return None

    # ── Public API ────────────────────────────────────────────────────

    def show_boot(self, version: str = "0.1.0") -> None:
        self._current_mode = DisplayMode.BOOT
        if not self._available:
            logger.info(f"[DISPLAY] Wundio v{version} – booting...")
            return

        def draw(d):
            d.rectangle([(0, 0), (self._width - 1, self._height - 1)], outline=255)
            d.text((10, 10), "Wundio",           fill=255)
            d.text((10, 28), f"v{version}",      fill=255)
            d.text((10, 46), "Starting...",       fill=255)
        self._draw(draw)

    def show_idle(self, message: str = "Bereit") -> None:
        self._current_mode = DisplayMode.IDLE
        if not self._available:
            logger.info(f"[DISPLAY] IDLE – {message}")
            return

        def draw(d):
            d.text((4, 4),  "Wundio",  fill=255)
            d.line([(0, 18), (128, 18)], fill=255)
            d.text((4, 24), message,   fill=255)
        self._draw(draw)

    def show_user_login(self, name: str, emoji: str = "🎵") -> None:
        self._current_mode = DisplayMode.USER_LOGIN
        if not self._available:
            logger.info(f"[DISPLAY] User login: {name}")
            return

        def draw(d):
            d.text((4, 4),  "Hallo!",    fill=255)
            d.line([(0, 18), (128, 18)], fill=255)
            # Emoji rendering on basic font is tricky – use name only
            d.text((4, 28), name[:16],   fill=255)
        self._draw(draw)

    def show_playing(self, track: str, artist: str, user: str = "") -> None:
        self._current_mode = DisplayMode.PLAYING
        if not self._available:
            logger.info(f"[DISPLAY] Playing: {track} – {artist}")
            return

        def draw(d):
            d.text((4, 2),  "▶ " + track[:16],   fill=255)
            d.text((4, 18), artist[:18],           fill=255)
            d.line([(0, 34), (128, 34)],           fill=255)
            if user:
                d.text((4, 40), f"@ {user[:14]}", fill=255)
        self._draw(draw)

    def show_setup(self, ssid: str, ip: str) -> None:
        self._current_mode = DisplayMode.SETUP
        if not self._available:
            logger.info(f"[DISPLAY] SETUP – SSID: {ssid}  IP: {ip}")
            return

        def draw(d):
            d.text((4, 2),  "Setup-Modus",         fill=255)
            d.line([(0, 16), (128, 16)],            fill=255)
            d.text((4, 20), f"WiFi: {ssid[:14]}",  fill=255)
            d.text((4, 34), f"IP:   {ip}",         fill=255)
            d.text((4, 50), "Browser oeffnen",      fill=255)
        self._draw(draw)

    def show_error(self, message: str) -> None:
        self._current_mode = DisplayMode.ERROR
        if not self._available:
            logger.error(f"[DISPLAY] ERROR – {message}")
            return

        def draw(d):
            d.text((4, 4),  "! Fehler",        fill=255)
            d.line([(0, 18), (128, 18)],        fill=255)
            d.text((4, 24), message[:18],       fill=255)
        self._draw(draw)

    def clear(self) -> None:
        if not self._available or self._device is None:
            return
        try:
            self._device.clear()
        except Exception:
            pass

    def teardown(self) -> None:
        self.clear()
        if self._device:
            try:
                self._device.cleanup()
            except Exception:
                pass


# ── Singleton ─────────────────────────────────────────────────────────────────

_display: Optional[OledDisplay] = None


def get_display() -> OledDisplay:
    global _display
    if _display is None:
        _display = OledDisplay()
    return _display
