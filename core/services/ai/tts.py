"""
Wundio – Text-to-Speech Service (Piper, local)
https://github.com/rhasspy/piper
Piper is a fast, lightweight neural TTS engine perfect for Raspberry Pi.

Install: sudo bash /opt/wundio/scripts/install-piper.sh
Default voice: de_DE-thorsten-medium (German, male)
"""

import asyncio
import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PIPER_BIN  = "/opt/wundio/bin/piper"
VOICE_DIR  = "/opt/wundio/voices"
DEFAULT_VOICE = "de_DE-thorsten-medium"

# Available German voices (downloaded on demand)
VOICES = {
    "de_DE-thorsten-medium":   "Thorsten (männlich, mittel)",
    "de_DE-eva_k-x_low":       "Eva (weiblich, schnell)",
    "de_DE-kerstin-low":       "Kerstin (weiblich, natürlich)",
}


class PiperTTSService:
    """
    Wraps Piper TTS binary.
    Falls back to espeak-ng if Piper is not installed.
    """

    def __init__(self, voice: str = DEFAULT_VOICE):
        self._voice = voice
        self._available = False
        self._fallback = False   # espeak-ng

    def setup(self) -> bool:
        if Path(PIPER_BIN).exists():
            self._available = True
            logger.info(f"Piper TTS ready – voice: {self._voice}")
            return True

        # Try system piper
        result = subprocess.run(["which", "piper"], capture_output=True)
        if result.returncode == 0:
            self._available = True
            logger.info("Piper TTS (system) ready")
            return True

        # Fallback: espeak-ng
        result2 = subprocess.run(["which", "espeak-ng"], capture_output=True)
        if result2.returncode == 0:
            self._fallback = True
            logger.warning("Piper not found – using espeak-ng fallback")
            return True

        logger.warning("No TTS engine available – voice output disabled")
        return False

    async def speak(self, text: str) -> bool:
        """Synthesize and play text. Returns True on success."""
        if not text.strip():
            return True

        if self._available:
            return await self._speak_piper(text)
        if self._fallback:
            return await self._speak_espeak(text)

        logger.info(f"[TTS mock] {text}")
        return True   # silent mock in dev

    async def _speak_piper(self, text: str) -> bool:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        piper_bin = PIPER_BIN if Path(PIPER_BIN).exists() else "piper"
        voice_file = Path(VOICE_DIR) / f"{self._voice}.onnx"

        cmd_synth = [
            piper_bin,
            "--model",       str(voice_file),
            "--output_file", tmp_path,
        ]
        cmd_play = ["aplay", "-q", tmp_path]

        try:
            # Pipe text into piper
            proc = await asyncio.create_subprocess_exec(
                *cmd_synth,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.communicate(input=text.encode())

            # Play result
            play = await asyncio.create_subprocess_exec(
                *cmd_play,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await play.wait()
            return True
        except Exception as e:
            logger.error(f"Piper TTS error: {e}")
            return False
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    async def _speak_espeak(self, text: str) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                "espeak-ng", "-v", "de", "-s", "140", text,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return True
        except Exception as e:
            logger.error(f"espeak-ng error: {e}")
            return False

    @property
    def available(self) -> bool:
        return self._available or self._fallback

    def set_voice(self, voice: str) -> None:
        if voice in VOICES:
            self._voice = voice
            logger.info(f"TTS voice changed to: {voice}")

    def list_voices(self) -> dict:
        return VOICES


_tts: Optional[PiperTTSService] = None


def get_tts_service() -> PiperTTSService:
    global _tts
    if _tts is None:
        _tts = PiperTTSService()
    return _tts
