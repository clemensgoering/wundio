"""
Wundio – RFID Service (RC522 via SPI)
Runs as a background asyncio task.
On each scan: looks up tag in DB, dispatches action.
"""

import asyncio
import logging
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

# Callback type: receives uid (hex str), returns None
RfidCallback = Callable[[str], Awaitable[None]]


class RfidService:
    def __init__(self, rst_pin: int = 25, spi_bus: int = 0, spi_dev: int = 0):
        self._rst_pin = rst_pin
        self._spi_bus = spi_bus
        self._spi_dev = spi_dev
        self._reader = None
        self._available = False
        self._running = False
        self._callback: Optional[RfidCallback] = None
        self._last_uid: Optional[str] = None
        self._debounce_seconds: float = 1.5  # avoid double-scan

    def on_scan(self, callback: RfidCallback) -> None:
        """Register async callback for tag scans."""
        self._callback = callback

    def setup(self) -> bool:
        try:
            from mfrc522 import SimpleMFRC522
            # SimpleMFRC522 is a convenience wrapper; we use the lower-level
            # MFRC522 for UID-only reads without blocking
            import RPi.GPIO as GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            self._reader = SimpleMFRC522()
            self._available = True
            logger.info("RFID RC522 initialized")
            return True
        except Exception as e:
            logger.warning(f"RFID not available: {e} – hardware absent or SPI not enabled")
            self._available = False
            return False

    async def run(self) -> None:
        """Main scan loop – run as asyncio task."""
        self._running = True

        if not self._available:
            logger.info("RFID service running in mock mode (no hardware)")
            while self._running:
                await asyncio.sleep(5)
            return

        logger.info("RFID scan loop started")
        while self._running:
            try:
                uid = await self._read_uid_async()
                if uid and uid != self._last_uid:
                    self._last_uid = uid
                    logger.info(f"RFID tag scanned: {uid}")
                    if self._callback:
                        await self._callback(uid)
                    await asyncio.sleep(self._debounce_seconds)
                else:
                    self._last_uid = None   # reset after debounce window
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"RFID scan error: {e}")
                await asyncio.sleep(1)

    async def _read_uid_async(self) -> Optional[str]:
        """Non-blocking UID read via thread executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._read_uid_blocking)

    def _read_uid_blocking(self) -> Optional[str]:
        """Blocking UID read – runs in thread pool."""
        if not self._reader:
            return None
        try:
            # Use the lower-level MFRC522_Request + MFRC522_SelectTagSN
            # for UID-only (no NDEF read needed)
            (status, _) = self._reader.READER.MFRC522_Request(
                self._reader.READER.PICC_REQIDL
            )
            if status != self._reader.READER.MI_OK:
                return None
            (status, uid_bytes) = self._reader.READER.MFRC522_SelectTagSN()
            if status != self._reader.READER.MI_OK:
                return None
            return "".join(f"{b:02X}" for b in uid_bytes)
        except Exception:
            return None

    async def write_uid_mock(self, uid: str) -> None:
        """Simulate a tag scan (for testing without hardware)."""
        if self._callback:
            logger.info(f"Mock RFID scan: {uid}")
            await self._callback(uid)

    def stop(self) -> None:
        self._running = False
        if self._available:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass


_service: Optional[RfidService] = None


def get_rfid_service() -> RfidService:
    global _service
    if _service is None:
        _service = RfidService()
    return _service
