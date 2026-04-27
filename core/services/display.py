"""
Wundio – Display Service

Abstraktion für alle unterstützten Display-Typen. Die Factory `get_display()`
liest `DISPLAY_TYPE` aus der Config und gibt den passenden Treiber zurück:

  none  → NullDisplay  (nur Logging, kein Hardware-Zugriff)
  oled  → OledDisplay  (luma.oled, SSD1306/SH1106, I2C)
  tft   → TftDisplay   (luma.lcd,  ST7735/ILI9341,  SPI)

Alle Treiber erben von `BaseDisplay` und implementieren dieselbe öffentliche
API. Der Rest der Anwendung importiert ausschließlich `get_display()` und kennt
keinen konkreten Treiber-Typ.

Hinweis TFT: Die TftDisplay-Implementierung folgt der luma.lcd-Schnittstelle.
Sie ist auf Pi-Hardware noch nicht vollständig abgenommen – Beiträge willkommen.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from config import get_settings

logger = logging.getLogger(__name__)


# ── Shared types ──────────────────────────────────────────────────────────────

class DisplayMode(str, Enum):
    BOOT       = "boot"
    IDLE       = "idle"
    PLAYING    = "playing"
    USER_LOGIN = "user_login"
    SETUP      = "setup"
    ERROR      = "error"


# ── Abstract base ─────────────────────────────────────────────────────────────

class BaseDisplay(ABC):
    """Common interface that all display drivers must implement.

    Every method is safe to call regardless of hardware availability – drivers
    fall back to console logging when the physical device is absent or fails to
    initialise.
    """

    def __init__(self) -> None:
        self._available    = False
        self._current_mode = DisplayMode.BOOT

    @property
    def available(self) -> bool:
        """True when the physical display was initialised successfully."""
        return self._available

    @abstractmethod
    def setup(self) -> bool:
        """Initialise the display hardware. Returns True on success."""

    @abstractmethod
    def clear(self) -> None:
        """Blank the display."""

    @abstractmethod
    def teardown(self) -> None:
        """Release hardware resources."""

    # ── Public screen methods ─────────────────────────────────────────────────

    @abstractmethod
    def show_boot(self, version: str = "0.1.0") -> None: ...

    @abstractmethod
    def show_idle(self, message: str = "Bereit") -> None: ...

    @abstractmethod
    def show_user_login(self, name: str) -> None: ...

    @abstractmethod
    def show_playing(self, track: str, artist: str, user: str = "") -> None: ...

    @abstractmethod
    def show_setup(self, ssid: str, ip: str) -> None: ...

    @abstractmethod
    def show_error(self, message: str) -> None: ...


# ── NullDisplay ───────────────────────────────────────────────────────────────

class NullDisplay(BaseDisplay):
    """No-op display used when DISPLAY_TYPE=none or as an emergency fallback.

    All screen methods log at INFO level so the rest of the application still
    produces meaningful output in headless / dev environments.
    """

    def setup(self) -> bool:
        self._available = True   # always "available" – nothing can fail
        logger.info("Display: NullDisplay active (no hardware output)")
        return True

    def clear(self) -> None:
        pass

    def teardown(self) -> None:
        pass

    def show_boot(self, version: str = "0.1.0") -> None:
        self._current_mode = DisplayMode.BOOT
        logger.info(f"[DISPLAY] Wundio v{version} – booting...")

    def show_idle(self, message: str = "Bereit") -> None:
        self._current_mode = DisplayMode.IDLE
        logger.info(f"[DISPLAY] IDLE – {message}")

    def show_user_login(self, name: str) -> None:
        self._current_mode = DisplayMode.USER_LOGIN
        logger.info(f"[DISPLAY] User login: {name}")

    def show_playing(self, track: str, artist: str, user: str = "") -> None:
        self._current_mode = DisplayMode.PLAYING
        logger.info(f"[DISPLAY] Playing: {track} – {artist}")

    def show_setup(self, ssid: str, ip: str) -> None:
        self._current_mode = DisplayMode.SETUP
        logger.info(f"[DISPLAY] SETUP – SSID: {ssid}  IP: {ip}")

    def show_error(self, message: str) -> None:
        self._current_mode = DisplayMode.ERROR
        logger.error(f"[DISPLAY] ERROR – {message}")


# ── OledDisplay ───────────────────────────────────────────────────────────────

class OledDisplay(BaseDisplay):
    """I2C OLED driver (luma.oled).

    Supports SSD1306 (default) and SH1106 controllers on 128×64 panels.
    Configured via wundio.env:
      DISPLAY_TYPE=oled
      DISPLAY_MODEL=ssd1306   # or sh1106
      DISPLAY_I2C_ADDRESS=0x3C
      DISPLAY_I2C_BUS=1
      DISPLAY_WIDTH=128
      DISPLAY_HEIGHT=64
    """

    def __init__(
        self,
        i2c_address: int = 0x3C,
        i2c_bus: int = 1,
        width: int = 128,
        height: int = 64,
        model: str = "ssd1306",
    ) -> None:
        super().__init__()
        self._address = i2c_address
        self._bus     = i2c_bus
        self._width   = width
        self._height  = height
        self._model   = model.lower()
        self._device  = None

    def setup(self) -> bool:
        """Initialise luma.oled. Falls back silently when hardware is absent."""
        try:
            from luma.core.interface.serial import i2c
            serial = i2c(port=self._bus, address=self._address)

            if self._model == "sh1106":
                from luma.oled.device import sh1106
                self._device = sh1106(serial, width=self._width, height=self._height)
            else:
                from luma.oled.device import ssd1306
                self._device = ssd1306(serial, width=self._width, height=self._height)

            self._available = True
            logger.info(
                f"OLED ({self._model}) initialised at I2C {hex(self._address)} "
                f"bus={self._bus} {self._width}×{self._height}"
            )
            return True
        except Exception as e:
            logger.warning(f"OLED not available: {e} – console fallback active")
            self._available = False
            return False

    def _draw(self, fn) -> None:
        """Execute a PIL draw callable inside a luma canvas context."""
        if not self._available or self._device is None:
            return
        try:
            from luma.core.render import canvas
            with canvas(self._device) as draw:
                fn(draw)
        except Exception as e:
            logger.error(f"OLED draw error: {e}")

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

    # ── Screen methods ────────────────────────────────────────────────────────

    def show_boot(self, version: str = "0.1.0") -> None:
        self._current_mode = DisplayMode.BOOT
        if not self._available:
            logger.info(f"[DISPLAY] Wundio v{version} – booting...")
            return

        def draw(d):
            d.rectangle([(0, 0), (self._width - 1, self._height - 1)], outline=255)
            d.text((10, 10), "Wundio",      fill=255)
            d.text((10, 28), f"v{version}", fill=255)
            d.text((10, 46), "Starting...", fill=255)
        self._draw(draw)

    def show_idle(self, message: str = "Bereit") -> None:
        self._current_mode = DisplayMode.IDLE
        if not self._available:
            logger.info(f"[DISPLAY] IDLE – {message}")
            return

        def draw(d):
            d.text((4, 4),  "Wundio",              fill=255)
            d.line([(0, 18), (self._width, 18)],   fill=255)
            d.text((4, 24), message,               fill=255)
        self._draw(draw)

    def show_user_login(self, name: str) -> None:
        """Show a greeting for the given child profile name."""
        self._current_mode = DisplayMode.USER_LOGIN
        if not self._available:
            logger.info(f"[DISPLAY] User login: {name}")
            return

        def draw(d):
            d.text((4, 4),  "Hallo!",    fill=255)
            d.line([(0, 18), (self._width, 18)], fill=255)
            # Emoji rendering is unreliable with the default bitmap font;
            # we render the name only.
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
            d.line([(0, 34), (self._width, 34)],  fill=255)
            if user:
                d.text((4, 40), f"@ {user[:14]}", fill=255)
        self._draw(draw)

    def show_setup(self, ssid: str, ip: str) -> None:
        self._current_mode = DisplayMode.SETUP
        if not self._available:
            logger.info(f"[DISPLAY] SETUP – SSID: {ssid}  IP: {ip}")
            return

        def draw(d):
            d.text((4, 2),  "Setup-Modus",        fill=255)
            d.line([(0, 16), (self._width, 16)],  fill=255)
            d.text((4, 20), f"WiFi: {ssid[:14]}", fill=255)
            d.text((4, 34), f"IP:   {ip}",        fill=255)
            d.text((4, 50), "Browser oeffnen",     fill=255)
        self._draw(draw)

    def show_error(self, message: str) -> None:
        self._current_mode = DisplayMode.ERROR
        if not self._available:
            logger.error(f"[DISPLAY] ERROR – {message}")
            return

        def draw(d):
            d.text((4, 4),  "! Fehler",           fill=255)
            d.line([(0, 18), (self._width, 18)],  fill=255)
            d.text((4, 24), message[:18],          fill=255)
        self._draw(draw)


# ── TftDisplay ────────────────────────────────────────────────────────────────

class TftDisplay(BaseDisplay):
    """SPI TFT driver (luma.lcd).

    Supports ST7735 (128×160) and ILI9341 (240×320) controllers.
    Configured via wundio.env:
      DISPLAY_TYPE=tft
      DISPLAY_MODEL=st7735    # or ili9341
      DISPLAY_SPI_BUS=0
      DISPLAY_SPI_DEV=1       # CE1 keeps CE0 free for RC522
      DISPLAY_DC_PIN=16
      DISPLAY_RST_PIN=20
      DISPLAY_WIDTH=128
      DISPLAY_HEIGHT=160

    Note: This driver has not been fully validated on physical hardware.
    Contributions and test reports are welcome – see CONTRIBUTING.md.
    """

    def __init__(
        self,
        spi_bus: int = 0,
        spi_dev: int = 1,
        dc_pin: int = 16,
        rst_pin: int = 20,
        width: int = 128,
        height: int = 160,
        model: str = "st7735",
    ) -> None:
        super().__init__()
        self._spi_bus = spi_bus
        self._spi_dev = spi_dev
        self._dc_pin  = dc_pin
        self._rst_pin = rst_pin
        self._width   = width
        self._height  = height
        self._model   = model.lower()
        self._device  = None

    def setup(self) -> bool:
        """Initialise luma.lcd. Falls back silently when hardware is absent."""
        try:
            from luma.core.interface.serial import spi
            serial = spi(
                bus=self._spi_bus,
                device=self._spi_dev,
                gpio_DC=self._dc_pin,
                gpio_RST=self._rst_pin,
            )

            if self._model == "ili9341":
                from luma.lcd.device import ili9341
                self._device = ili9341(serial, width=self._width, height=self._height)
            else:
                from luma.lcd.device import st7735
                self._device = st7735(serial, width=self._width, height=self._height)

            self._available = True
            logger.info(
                f"TFT ({self._model}) initialised on SPI bus={self._spi_bus} "
                f"dev={self._spi_dev} {self._width}×{self._height}"
            )
            return True
        except Exception as e:
            logger.warning(f"TFT not available: {e} – console fallback active")
            self._available = False
            return False

    def _draw(self, fn) -> None:
        if not self._available or self._device is None:
            return
        try:
            from luma.core.render import canvas
            with canvas(self._device) as draw:
                fn(draw)
        except Exception as e:
            logger.error(f"TFT draw error: {e}")

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

    # ── Screen methods (adapted for wider TFT canvas) ─────────────────────────

    def show_boot(self, version: str = "0.1.0") -> None:
        self._current_mode = DisplayMode.BOOT
        if not self._available:
            logger.info(f"[DISPLAY] Wundio v{version} – booting...")
            return

        def draw(d):
            d.rectangle([(0, 0), (self._width - 1, self._height - 1)], outline="white")
            d.text((10, 20), "Wundio",      fill="white")
            d.text((10, 50), f"v{version}", fill="white")
            d.text((10, 80), "Starting...", fill="white")
        self._draw(draw)

    def show_idle(self, message: str = "Bereit") -> None:
        self._current_mode = DisplayMode.IDLE
        if not self._available:
            logger.info(f"[DISPLAY] IDLE – {message}")
            return

        def draw(d):
            d.text((8, 8),   "Wundio",                              fill="white")
            d.line([(0, 30), (self._width, 30)],                    fill="white")
            d.text((8, 40),  message,                               fill="white")
        self._draw(draw)

    def show_user_login(self, name: str) -> None:
        self._current_mode = DisplayMode.USER_LOGIN
        if not self._available:
            logger.info(f"[DISPLAY] User login: {name}")
            return

        def draw(d):
            d.text((8, 8),   "Hallo!",                              fill="white")
            d.line([(0, 30), (self._width, 30)],                    fill="white")
            d.text((8, 45),  name[:20],                             fill="white")
        self._draw(draw)

    def show_playing(self, track: str, artist: str, user: str = "") -> None:
        self._current_mode = DisplayMode.PLAYING
        if not self._available:
            logger.info(f"[DISPLAY] Playing: {track} – {artist}")
            return

        def draw(d):
            d.text((8, 8),   "▶ " + track[:20],  fill="white")
            d.text((8, 30),  artist[:22],          fill="white")
            d.line([(0, 50), (self._width, 50)],  fill="white")
            if user:
                d.text((8, 60), f"@ {user[:18]}", fill="white")
        self._draw(draw)

    def show_setup(self, ssid: str, ip: str) -> None:
        self._current_mode = DisplayMode.SETUP
        if not self._available:
            logger.info(f"[DISPLAY] SETUP – SSID: {ssid}  IP: {ip}")
            return

        def draw(d):
            d.text((8, 8),   "Setup-Modus",        fill="white")
            d.line([(0, 28), (self._width, 28)],   fill="white")
            d.text((8, 38),  f"WiFi: {ssid[:18]}", fill="white")
            d.text((8, 58),  f"IP:   {ip}",        fill="white")
            d.text((8, 78),  "Browser oeffnen",     fill="white")
        self._draw(draw)

    def show_error(self, message: str) -> None:
        self._current_mode = DisplayMode.ERROR
        if not self._available:
            logger.error(f"[DISPLAY] ERROR – {message}")
            return

        def draw(d):
            d.text((8, 8),   "! Fehler",           fill="white")
            d.line([(0, 28), (self._width, 28)],   fill="white")
            d.text((8, 40),  message[:22],          fill="white")
        self._draw(draw)


# ── Factory ───────────────────────────────────────────────────────────────────

def _build_display() -> BaseDisplay:
    """Construct the correct display driver from wundio.env settings.

    Falls back to NullDisplay on any configuration or import error so the
    application always has a valid display object to call.
    """
    try:
        cfg          = get_settings()
        display_type = cfg.display_type.lower()

        if display_type == "oled":
            return OledDisplay(
                i2c_address=cfg.display_i2c_address,
                i2c_bus=cfg.display_i2c_bus,
                width=cfg.display_width,
                height=cfg.display_height,
                model=cfg.display_model,
            )

        if display_type == "tft":
            return TftDisplay(
                spi_bus=cfg.display_spi_bus,
                spi_dev=cfg.display_spi_dev,
                dc_pin=cfg.display_dc_pin,
                rst_pin=cfg.display_rst_pin,
                width=cfg.display_width,
                height=cfg.display_height,
                model=cfg.display_model,
            )

        # display_type == "none" or anything unrecognised
        if display_type not in ("none", ""):
            logger.warning(f"Unknown DISPLAY_TYPE '{display_type}' – using NullDisplay")
        return NullDisplay()

    except Exception as e:
        logger.warning(f"Display factory error: {e} – using NullDisplay")
        return NullDisplay()


# ── Singleton ─────────────────────────────────────────────────────────────────

_display: Optional[BaseDisplay] = None


def get_display() -> BaseDisplay:
    """Return the application-wide display singleton.

    The instance is created on first call using `_build_display()` and reused
    for the lifetime of the process. Reset `_display = None` in tests to force
    re-creation with different config.
    """
    global _display
    if _display is None:
        _display = _build_display()
    return _display