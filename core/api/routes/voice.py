"""
Wundio – /api/voice routes (Phase 3)
"""
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from services.ai.stt    import get_stt_service
from services.ai.tts    import get_tts_service, VOICES
from services.ai.wake   import get_wake_service
from services.ai.intent import parse
from services.ai.voice  import get_voice_orchestrator
from database import get_setting, set_setting, log_event

router = APIRouter(tags=["voice"])
logger = logging.getLogger(__name__)


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = None


class TextRequest(BaseModel):
    text: str


class WakeWordConfig(BaseModel):
    phrase: str


class VoiceConfig(BaseModel):
    enabled: bool
    wake_phrase: Optional[str] = None
    tts_voice: Optional[str] = None
    whisper_model: Optional[str] = None


@router.get("/status")
async def voice_status():
    """Current voice pipeline availability."""
    stt  = get_stt_service()
    tts  = get_tts_service()
    wake = get_wake_service()
    return {
        "stt_available":  stt.available,
        "stt_model":      stt.model_name,
        "tts_available":  tts.available,
        "tts_voice":      tts._voice,
        "wake_available": wake.available,
        "wake_phrase":    wake.phrase,
        "voice_enabled":  get_setting("voice_enabled") == "true",
    }


@router.post("/speak")
async def speak(req: SpeakRequest):
    """Synthesize and play text immediately."""
    tts = get_tts_service()
    if req.voice:
        tts.set_voice(req.voice)
    ok = await tts.speak(req.text)
    log_event("voice", f"TTS: '{req.text[:60]}'")
    return {"ok": ok, "text": req.text}


@router.get("/voices")
async def list_voices():
    """Available TTS voices."""
    return {"voices": VOICES}


@router.post("/parse-intent")
async def parse_intent(req: TextRequest):
    """Parse text → intent (for testing without microphone)."""
    intent = parse(req.text)
    log_event("voice", f"Intent parse: '{req.text}' → {intent.type}")
    return intent.to_dict()


@router.post("/process")
async def process_text(req: TextRequest):
    """
    Full pipeline: text → intent → action → TTS response.
    Bypasses microphone – useful for testing or chat-style interaction.
    """
    orchestrator = get_voice_orchestrator()
    intent = await orchestrator.handle_text(req.text)
    log_event("voice", f"Processed: '{req.text}' → {intent.type}")
    return intent.to_dict()


@router.post("/simulate-wake")
async def simulate_wake():
    """Trigger a simulated wake-word event (dev/testing)."""
    orchestrator = get_voice_orchestrator()
    await orchestrator.simulate_wake()
    log_event("voice", "Wake simulated via API")
    return {"ok": True}


@router.put("/config")
async def update_voice_config(cfg: VoiceConfig):
    """Enable/disable voice features and set preferences."""
    set_setting("voice_enabled", "true" if cfg.enabled else "false")

    if cfg.wake_phrase:
        wake = get_wake_service()
        wake.set_phrase(cfg.wake_phrase)
        set_setting("wake_phrase", cfg.wake_phrase)

    if cfg.tts_voice:
        if cfg.tts_voice not in VOICES:
            raise HTTPException(status_code=422, detail=f"Unknown voice. Available: {list(VOICES.keys())}")
        get_tts_service().set_voice(cfg.tts_voice)
        set_setting("tts_voice", cfg.tts_voice)

    log_event("voice", f"Config updated: enabled={cfg.enabled}")
    return {"ok": True}


@router.post("/set-wake-phrase")
async def set_wake_phrase(cfg: WakeWordConfig):
    if len(cfg.phrase.strip()) < 3:
        raise HTTPException(status_code=422, detail="Phrase too short (min 3 chars)")
    get_wake_service().set_phrase(cfg.phrase)
    set_setting("wake_phrase", cfg.phrase)
    log_event("voice", f"Wake phrase: '{cfg.phrase}'")
    return {"phrase": cfg.phrase}
