"""
Wundio – Voice Orchestrator
Full pipeline:
  wake-word → record audio → Whisper STT → intent parse → dispatch action → Piper TTS response

Designed to be modular: each step can be replaced or skipped independently.
"""

import asyncio
import logging
from typing import Optional

from services.ai.stt    import WhisperService, get_stt_service
from services.ai.tts    import PiperTTSService, get_tts_service
from services.ai.wake   import WakeWordService, get_wake_service
from services.ai.intent import parse, Intent

logger = logging.getLogger(__name__)

# Response templates (no LLM needed)
RESPONSES = {
    "volume_up":    "Ich mache es lauter.",
    "volume_down":  "Ich mache es leiser.",
    "play":         "Musik läuft!",
    "pause":        "Ich pause die Musik.",
    "next":         "Nächstes Lied.",
    "prev":         "Vorheriges Lied.",
    "greeting":     "Hallo! Ich bin Wundio. Was soll ich spielen?",
    "play_playlist":"Ich suche {query} für dich.",
    "user_switch":  "Hallo {name}!",
    "unknown":      "Das habe ich leider nicht verstanden. Versuch es nochmal!",
}


class VoiceOrchestrator:
    def __init__(
        self,
        stt:  Optional[WhisperService]  = None,
        tts:  Optional[PiperTTSService] = None,
        wake: Optional[WakeWordService] = None,
    ):
        self._stt  = stt  or get_stt_service()
        self._tts  = tts  or get_tts_service()
        self._wake = wake or get_wake_service()
        self._listening = False
        self._action_callback = None

    def on_action(self, callback) -> None:
        """Register callback for dispatched intents: async fn(intent: Intent) -> None"""
        self._action_callback = callback

    def setup(self, pi_generation: int = 3) -> bool:
        ok_stt  = self._stt.setup()
        ok_tts  = self._tts.setup()
        ok_wake = self._wake.setup(pi_generation=pi_generation)

        # Wire wake-word to our listen handler
        self._wake.on_wake(self._on_wake_triggered)

        logger.info(
            f"Voice pipeline: STT={'✓' if ok_stt else '✗'} "
            f"TTS={'✓' if ok_tts else '✗'} "
            f"Wake={'✓' if ok_wake else '✗'}"
        )
        return ok_wake   # wake is the gate; STT/TTS can be partial

    async def run(self) -> None:
        """Start the wake-word detection loop (long-running task)."""
        await self._wake.run()

    async def _on_wake_triggered(self) -> None:
        """Called when wake-word is detected. Records, transcribes, acts."""
        if self._listening:
            return   # already in a session
        self._listening = True

        try:
            # Acknowledge
            await self._tts.speak("Ja?")

            # Record & transcribe
            text = await self._stt.record_and_transcribe(duration=5.0)
            if not text:
                await self._tts.speak("Ich habe nichts gehört.")
                return

            logger.info(f"Voice: '{text}'")

            # Parse intent
            intent = parse(text)
            logger.info(f"Intent: {intent.to_dict()}")

            # Respond
            response = self._build_response(intent)
            await self._tts.speak(response)

            # Dispatch action
            if self._action_callback:
                await self._action_callback(intent)

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}")
            await self._tts.speak("Entschuldigung, da ist etwas schiefgelaufen.")
        finally:
            self._listening = False

    def _build_response(self, intent: Intent) -> str:
        template = RESPONSES.get(intent.type, RESPONSES["unknown"])
        try:
            return template.format(**intent.params)
        except KeyError:
            return template

    async def handle_text(self, text: str) -> Intent:
        """
        Process arbitrary text through the pipeline (for API/testing).
        Skips recording – useful for debugging intent parsing.
        """
        intent = parse(text)
        response = self._build_response(intent)
        await self._tts.speak(response)
        if self._action_callback:
            await self._action_callback(intent)
        return intent

    async def simulate_wake(self) -> None:
        await self._wake.simulate_wake()

    def stop(self) -> None:
        self._wake.stop()


_orchestrator: Optional[VoiceOrchestrator] = None


def get_voice_orchestrator() -> VoiceOrchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = VoiceOrchestrator()
    return _orchestrator
