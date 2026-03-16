"""
Wundio – RFID Service
Supports RC522 (SPI, mfrc522) and PN532 (I2C, adafruit-circuitpython-pn532).
Driver is selected via RFID_TYPE in wundio.env.

Config keys:
  RFID_TYPE=rc522|pn532        (default: rc522)
  RFID_RST_PIN=25              (RC522 only, BCM)
  RFID_SPI_BUS=0               (RC522 only)
  RFID_SPI_DEV=0               (RC522 only, CE0)
  RFID_I2C_BUS=1               (PN532 only)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

RfidCallback = Callable[[str], Awaitable[None]]

DEBOUNCE_SECONDS = 1.5


# ── Abstract base ──────────────────────────────────────────────────────────────

class RfidDriver(ABC):
    """
    Common interface for RFID/NFC backends.
    All methods are safe to call without hardware.
    """

    def __init__(self):
        self._available = False

    @abstractmethod
    def setup(self) -> bool:
        """Initialize hardware. Returns True when reader is ready."""

    @abstractmethod
    def read_uid_blocking(self) -> Optional[str]:
        """
        Blocking single-read attempt.
        Returns UID as uppercase hex string (e.g. '04A3F21B')
        or None when no tag is present.
        Must be fast enough to be polled at 10 Hz.
        """

    @property
    def available(self) -> bool:
        return self._available

    def teardown(self) -> None:
        """Release GPIO / I2C resources."""


# ── RC522 driver (SPI) ─────────────────────────────────────────────────────────

class RC522Driver(RfidDriver):
    """
    mfrc522 library backend.
    Tested with: https://github.com/pimylifeup/MFRC522-python (v0.0.7)
    Wiring: CE0=Pin24, SCLK=Pin23, MOSI=Pin19, MISO=Pin21, RST=BCM25/Pin22
    """

    def __init__(self, rst_pin: int = 25, spi_bus: int = 0, spi_dev: int = 0):
        super().__init__()
        self._rst_pin = rst_pin
        self._spi_bus = spi_bus
        self._spi_dev = spi_dev
        self._reader = None

    def setup(self) -> bool:
        try:
            from mfrc522 import SimpleMFRC522
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            self._reader = SimpleMFRC522()
            self._available = True
            logger.info(f"RC522 initialized (SPI bus={self._spi_bus} dev={self._spi_dev} rst=BCM{self._rst_pin})")
            return True
        except Exception as e:
            logger.warning(f"RC522 not available: {e}")
            return False

    def read_uid_blocking(self) -> Optional[str]:
        if not self._reader:
            return None
        try:
            reader = self._reader.READER
            (status, _) = reader.MFRC522_Request(reader.PICC_REQIDL)
            if status != reader.MI_OK:
                return None
            (status, uid_bytes) = reader.MFRC522_Anticoll()
            if status != reader.MI_OK:
                return None
            return "".join(f"{b:02X}" for b in uid_bytes)
        except Exception:
            return None

    def teardown(self) -> None:
        if self._available:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass


# ── PN532 driver (I2C) ─────────────────────────────────────────────────────────

class PN532Driver(RfidDriver):
    """
    Adafruit CircuitPython PN532 backend (I2C).
    Library: adafruit-circuitpython-pn532 (installed by install.sh when RFID_TYPE=pn532)
    Wiring: SDA=BCM2/Pin3, SCL=BCM3/Pin5, GND, 3.3V
    Advantages over RC522:
      - Shares I2C bus with OLED → 2 fewer wires
      - NFC tag compatible (ISO 14443A/B, Mifare, NTAG)
      - More reliable library (Adafruit maintained)
      - Longer read range (~5cm vs ~3cm)
    """

    def __init__(self, i2c_bus: int = 1):
        super().__init__()
        self._i2c_bus = i2c_bus
        self._pn532 = None

    def setup(self) -> bool:
        try:
            import board
            import busio
            from adafruit_pn532.i2c import PN532_I2C

            i2c = busio.I2C(board.SCL, board.SDA)
            self._pn532 = PN532_I2C(i2c, debug=False)
            ic, ver, rev, support = self._pn532.firmware_version
            self._pn532.SAM_configuration()
            self._available = True
            logger.info(f"PN532 initialized (I2C bus={self._i2c_bus}) firmware v{ver}.{rev}")
            return True
        except Exception as e:
            logger.warning(f"PN532 not available: {e}")
            return False

    def read_uid_blocking(self) -> Optional[str]:
        if not self._pn532:
            return None
        try:
            # timeout_sec=0.1 → non-blocking poll
            uid = self._pn532.read_passive_target(timeout=0.1)
            if uid is None:
                return None
            return "".join(f"{b:02X}" for b in uid)
        except Exception:
            return None

    def teardown(self) -> None:
        # adafruit-blinka handles I2C cleanup automatically
        pass


# ── Service (driver-agnostic) ──────────────────────────────────────────────────

class RfidService:
    """
    Async scan loop that wraps any RfidDriver.
    Existing callers are unaffected – API identical to previous version.
    """

    def __init__(self, driver: Optional[RfidDriver] = None):
        self._driver = driver
        self._running = False
        self._callback: Optional[RfidCallback] = None
        self._last_uid: Optional[str] = None

    def on_scan(self, callback: RfidCallback) -> None:
        self._callback = callback

    def setup(self) -> bool:
        if self._driver is None:
            self._driver = _build_driver_from_config()
        return self._driver.setup()

    @property
    def available(self) -> bool:
        return self._driver.available if self._driver else False

    async def run(self) -> None:
        self._running = True

        if not self.available:
            logger.info("RFID service running in mock mode (no hardware)")
            while self._running:
                await asyncio.sleep(5)
            return

        driver_name = type(self._driver).__name__
        logger.info(f"RFID scan loop started ({driver_name})")

        while self._running:
            try:
                uid = await self._read_async()
                if uid and uid != self._last_uid:
                    self._last_uid = uid
                    logger.info(f"RFID tag scanned: {uid}")
                    if self._callback:
                        await self._callback(uid)
                    await asyncio.sleep(DEBOUNCE_SECONDS)
                else:
                    if uid is None:
                        self._last_uid = None
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"RFID scan error: {e}")
                await asyncio.sleep(1)

    async def _read_async(self) -> Optional[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._driver.read_uid_blocking)

    async def simulate_scan(self, uid: str) -> None:
        """Inject a virtual tag scan (testing / dev mode)."""
        logger.info(f"Simulated RFID scan: {uid}")
        if self._callback:
            await self._callback(uid)

    # backward-compat alias
    async def write_uid_mock(self, uid: str) -> None:
        await self.simulate_scan(uid)

    def stop(self) -> None:
        self._running = False
        if self._driver:
            self._driver.teardown()


# ── Factory ────────────────────────────────────────────────────────────────────

def _build_driver_from_config() -> RfidDriver:
    try:
        from config import get_settings
        cfg = get_settings()
        rfid_type = getattr(cfg, "rfid_type", "rc522").lower()
    except Exception:
        rfid_type = "rc522"

    if rfid_type == "pn532":
        try:
            from config import get_settings
            cfg = get_settings()
            return PN532Driver(i2c_bus=getattr(cfg, "rfid_i2c_bus", 1))
        except Exception:
            return PN532Driver()

    # Default: RC522
    try:
        from config import get_settings
        cfg = get_settings()
        return RC522Driver(
            rst_pin = cfg.rfid_rst_pin,
            spi_bus = cfg.rfid_spi_bus,
            spi_dev = cfg.rfid_spi_dev,
        )
    except Exception:
        return RC522Driver()


# ── Singleton ──────────────────────────────────────────────────────────────────

_service: Optional[RfidService] = None


def get_rfid_service() -> RfidService:
    global _service
    if _service is None:
        _service = RfidService()
    return _service