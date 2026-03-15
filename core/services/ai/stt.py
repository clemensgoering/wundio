"""
Wundio – Speech-to-Text Service (OpenAI Whisper, local)
Runs transcription in a thread pool to avoid blocking the event loop.
Supported models: tiny (Pi 3/4) · base · small (Pi 5)
"""

import asyncio
import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# WAV capture command (requires arecord from alsa-utils)
ARECORD_CMD = [
    "arecord",
    "--device=default",
    "--format=S16_LE",
    "--rate=16000",
    "--channels=1",
    "--duration={duration}",
    "{output_file}",
]


class WhisperService:
    """
    Wraps openai-whisper for local speech recognition.
    Falls back gracefully when whisper is not installed or no mic available.
    """

    def __init__(self, model_name: str = "tiny"):
        self._model_name = model_name
        self._model = None
        self._available = False
        self._loading = False

    def setup(self) -> bool:
        """Load the Whisper model. Blocks – call once at startup."""
        try:
            import whisper
            logger.info(f"Loading Whisper model '{self._model_name}'…")
            t0 = time.monotonic()
            self._model = whisper.load_model(self._model_name)
            elapsed = time.monotonic() - t0
            logger.info(f"Whisper '{self._model_name}' ready in {elapsed:.1f}s")
            self._available = True
            return True
        except ImportError:
            logger.warning("openai-whisper not installed – STT unavailable")
            return False
        except Exception as e:
            logger.warning(f"Whisper setup failed: {e}")
            return False

    async def transcribe_file(self, audio_path: str) -> Optional[str]:
        """Transcribe an audio file. Returns text or None on error."""
        if not self._available or self._model is None:
            return None
        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(
                None, self._transcribe_blocking, audio_path
            )
            return result
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    def _transcribe_blocking(self, audio_path: str) -> str:
        result = self._model.transcribe(
            audio_path,
            language="de",
            task="transcribe",
            fp16=False,       # Pi doesn't have GPU
        )
        text = result.get("text", "").strip()
        logger.info(f"Whisper transcript: '{text}'")
        return text

    async def record_and_transcribe(self, duration: float = 4.0) -> Optional[str]:
        """Record {duration}s of audio and transcribe. Requires arecord."""
        import subprocess
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name

        cmd = [
            "arecord", f"--device=default", "--format=S16_LE",
            "--rate=16000", "--channels=1",
            f"--duration={int(duration)}", tmp_path,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
            return await self.transcribe_file(tmp_path)
        except FileNotFoundError:
            logger.warning("arecord not found – cannot record audio")
            return None
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    @property
    def available(self) -> bool:
        return self._available

    @property
    def model_name(self) -> str:
        return self._model_name


# ── Singleton ─────────────────────────────────────────────────────────────────

_stt: Optional[WhisperService] = None


def get_stt_service() -> WhisperService:
    global _stt
    if _stt is None:
        _stt = WhisperService()
    return _stt
