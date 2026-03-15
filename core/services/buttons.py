"""
Wundio – Button Service (GPIO, BCM mode)
Handles physical buttons with debounce and async callbacks.
Falls back gracefully when RPi.GPIO is unavailable (dev machine).
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Dict, Optional

logger = logging.getLogger(__name__)

ButtonCallback = Callable[[str], Awaitable[None]]

DEBOUNCE_MS = 200   # ignore bounces within this window


@dataclass
class ButtonConfig:
    name: str
    pin: int                   # BCM pin number
    pull_up: bool = True       # use internal pull-up


class ButtonService:
    def __init__(self):
        self._buttons: Dict[str, ButtonConfig] = {}
        self._callback: Optional[ButtonCallback] = None
        self._last_press: Dict[str, float] = {}
        self._available = False
        self._running = False
        self._gpio = None

    def register(self, name: str, pin: int, pull_up: bool = True) -> None:
        self._buttons[name] = ButtonConfig(name=name, pin=pin, pull_up=pull_up)

    def on_press(self, callback: ButtonCallback) -> None:
        self._callback = callback

    def setup(self) -> bool:
        if not self._buttons:
            logger.warning("No buttons registered")
            return False
        try:
            import RPi.GPIO as GPIO
            self._gpio = GPIO
            GPIO.setwarnings(False)
            GPIO.setmode(GPIO.BCM)
            for btn in self._buttons.values():
                pud = GPIO.PUD_UP if btn.pull_up else GPIO.PUD_DOWN
                GPIO.setup(btn.pin, GPIO.IN, pull_up_down=pud)
            self._available = True
            logger.info(f"Buttons initialized: {list(self._buttons.keys())}")
            return True
        except Exception as e:
            logger.warning(f"GPIO buttons not available: {e}")
            self._available = False
            return False

    async def run(self) -> None:
        self._running = True
        if not self._available:
            logger.info("Button service in mock mode")
            while self._running:
                await asyncio.sleep(5)
            return

        logger.info("Button poll loop started")
        # Poll-based approach – works on all Pi models without edge detection issues
        prev_state: Dict[str, int] = {}
        for btn in self._buttons.values():
            prev_state[btn.name] = 1  # HIGH = not pressed (pull-up)

        while self._running:
            for btn in self._buttons.values():
                try:
                    current = self._gpio.input(btn.pin)
                    if current == 0 and prev_state[btn.name] == 1:
                        # Falling edge = button pressed
                        now = time.monotonic()
                        last = self._last_press.get(btn.name, 0)
                        if (now - last) * 1000 >= DEBOUNCE_MS:
                            self._last_press[btn.name] = now
                            logger.info(f"Button pressed: {btn.name}")
                            if self._callback:
                                await self._callback(btn.name)
                    prev_state[btn.name] = current
                except Exception as e:
                    logger.error(f"Button read error ({btn.name}): {e}")
            await asyncio.sleep(0.05)   # 50ms poll = fast enough for buttons

    async def simulate_press(self, name: str) -> None:
        """Simulate a button press (for testing/dev)."""
        if name not in self._buttons:
            logger.warning(f"simulate_press: unknown button '{name}'")
            return
        logger.info(f"Simulated button press: {name}")
        if self._callback:
            await self._callback(name)

    def stop(self) -> None:
        self._running = False
        if self._available and self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass


def build_default_service(cfg) -> ButtonService:
    """Build the standard 5-button layout from config."""
    svc = ButtonService()
    svc.register("play_pause", cfg.button_play_pause_pin)
    svc.register("next",       cfg.button_next_pin)
    svc.register("prev",       cfg.button_prev_pin)
    svc.register("vol_up",     cfg.button_vol_up_pin)
    svc.register("vol_down",   cfg.button_vol_down_pin)
    return svc


_service: Optional[ButtonService] = None


def get_button_service() -> ButtonService:
    global _service
    if _service is None:
        _service = ButtonService()
    return _service
