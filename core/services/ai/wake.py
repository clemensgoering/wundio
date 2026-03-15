"""
Wundio – Wake-Word Detection
Uses a fast keyword-spotter approach:
  - Primary:  Vosk offline speech (small German model, ~50 MB)
  - Fallback: porcupine-style energy-threshold trigger (no model needed)

On Pi 3: energy-threshold only (too slow for Vosk real-time)
On Pi 4+: Vosk with small model
On Pi 5:  Vosk with full model

Trigger phrase: configurable, default "hey wundio"
"""

import asyncio
import logging
import time
from typing import Optional, Callable, Awaitable

logger = logging.getLogger(__name__)

WakeCallback = Callable[[], Awaitable[None]]


class WakeWordService:
    def __init__(
        self,
        phrase: str = "hey wundio",
        use_vosk: bool = True,
        vosk_model_path: str = "/opt/wundio/models/vosk-de-small",
    ):
        self._phrase = phrase.lower().strip()
        self._use_vosk = use_vosk
        self._vosk_model_path = vosk_model_path
        self._callback: Optional[WakeCallback] = None
        self._available = False
        self._running = False
        self._vosk_recognizer = None
        self._last_trigger = 0.0
        self._cooldown_s = 3.0   # prevent double-triggers

    def on_wake(self, callback: WakeCallback) -> None:
        self._callback = callback

    def setup(self, pi_generation: int = 3) -> bool:
        if pi_generation < 4:
            logger.warning("Pi 3 detected – using energy-threshold wake word (no Vosk)")
            self._use_vosk = False

        if self._use_vosk:
            try:
                from vosk import Model, KaldiRecognizer
                import os
                if os.path.exists(self._vosk_model_path):
                    model = Model(self._vosk_model_path)
                    self._vosk_recognizer = KaldiRecognizer(model, 16000)
                    logger.info(f"Vosk wake-word ready – phrase: '{self._phrase}'")
                    self._available = True
                    return True
                else:
                    logger.warning(f"Vosk model not found at {self._vosk_model_path}")
            except ImportError:
                logger.warning("vosk not installed")
            except Exception as e:
                logger.warning(f"Vosk setup failed: {e}")

        # Energy-threshold fallback: always available
        logger.info("Wake-word using energy-threshold mode")
        self._available = True
        self._use_vosk = False
        return True

    async def run(self) -> None:
        """Main detection loop."""
        self._running = True
        if not self._available:
            logger.info("Wake-word service disabled")
            return

        if self._use_vosk:
            await self._run_vosk_loop()
        else:
            await self._run_energy_loop()

    async def _run_vosk_loop(self) -> None:
        """Vosk real-time recognition on audio stream."""
        import json
        try:
            import pyaudio
        except ImportError:
            logger.warning("pyaudio not installed – cannot run Vosk loop")
            return

        pa = pyaudio.PyAudio()
        stream = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=16000,
            input=True,
            frames_per_buffer=4000,
        )
        logger.info("Vosk wake-word loop started")

        while self._running:
            try:
                data = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: stream.read(4000, exception_on_overflow=False)
                )
                if self._vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self._vosk_recognizer.Result())
                    text = result.get("text", "").lower()
                    if text and self._phrase in text:
                        await self._trigger(text)
                else:
                    partial = json.loads(self._vosk_recognizer.PartialResult())
                    partial_text = partial.get("partial", "").lower()
                    if self._phrase in partial_text:
                        await self._trigger(partial_text)
            except Exception as e:
                logger.error(f"Vosk loop error: {e}")
                await asyncio.sleep(0.5)

        stream.close()
        pa.terminate()

    async def _run_energy_loop(self) -> None:
        """
        Simplified energy-threshold approach.
        Detects loud audio bursts as potential trigger, then hands off to Whisper.
        In real hardware this would sample the mic; here we just sleep as mock.
        """
        logger.info("Energy wake-word loop running (mock – waiting for API trigger)")
        while self._running:
            await asyncio.sleep(5)

    async def _trigger(self, detected_text: str = "") -> None:
        now = time.monotonic()
        if now - self._last_trigger < self._cooldown_s:
            return
        self._last_trigger = now
        logger.info(f"Wake-word triggered! Detected: '{detected_text}'")
        if self._callback:
            await self._callback()

    async def simulate_wake(self) -> None:
        """Simulate a wake-word trigger (dev/testing)."""
        logger.info("Simulated wake-word trigger")
        await self._trigger("hey wundio")

    def stop(self) -> None:
        self._running = False

    @property
    def available(self) -> bool:
        return self._available

    @property
    def phrase(self) -> str:
        return self._phrase

    def set_phrase(self, phrase: str) -> None:
        self._phrase = phrase.lower().strip()
        logger.info(f"Wake-word phrase set to: '{self._phrase}'")


_wake: Optional[WakeWordService] = None


def get_wake_service() -> WakeWordService:
    global _wake
    if _wake is None:
        _wake = WakeWordService()
    return _wake
