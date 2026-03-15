"""
Phase 3 – Voice Pipeline Tests
All tests run without microphone, Piper binary or Whisper model.
"""
import pytest
import asyncio


# ── Intent Parser ─────────────────────────────────────────────────────────────

class TestIntentParser:
    """Tests for the keyword-based intent parser – no AI needed."""

    def _parse(self, text: str):
        from services.ai.intent import parse
        return parse(text)

    # Volume
    def test_volume_up_basic(self):
        i = self._parse("hey wundio lauter bitte")
        assert i.type == "volume_up"

    def test_volume_up_german(self):
        i = self._parse("lautstärke erhöhen")
        assert i.type == "volume_up"

    def test_volume_down_basic(self):
        i = self._parse("leiser machen")
        assert i.type == "volume_down"

    def test_volume_with_amount_percent(self):
        i = self._parse("20% lauter")
        assert i.type == "volume_up"
        assert i.params.get("amount") == 20

    def test_volume_with_word(self):
        i = self._parse("zehn prozent lauter")
        assert i.params.get("amount") == 10

    # Playback
    def test_next_track(self):
        assert self._parse("nächstes lied").type == "next"

    def test_next_track_english(self):
        assert self._parse("skip").type == "next"

    def test_prev_track(self):
        assert self._parse("zurück").type == "prev"

    def test_pause(self):
        assert self._parse("pause").type == "pause"

    def test_stop(self):
        assert self._parse("stop").type == "pause"

    def test_music_off(self):
        assert self._parse("musik aus").type == "pause"

    # Playlist
    def test_play_playlist_german(self):
        i = self._parse("spiele kinderliedere")
        assert i.type == "play_playlist"
        assert "kinderlieder" in i.params.get("query", "").lower() or \
               "kinderliedere" in i.params.get("query", "").lower()

    def test_play_with_artist(self):
        i = self._parse("ich möchte die Schlümpfe hören")
        assert i.type == "play_playlist"
        assert "schlümpfe" in i.params.get("query", "").lower()

    # User switch
    def test_user_switch_german(self):
        i = self._parse("ich bin Lena")
        assert i.type == "user_switch"
        assert "lena" in i.params.get("name", "").lower()

    def test_user_switch_wechsel(self):
        i = self._parse("wechsele zu Jonas")
        assert i.type == "user_switch"

    # Greeting
    def test_greeting_hallo(self):
        assert self._parse("hallo").type == "greeting"

    def test_greeting_hey(self):
        assert self._parse("hey").type == "greeting"

    # Unknown
    def test_unknown(self):
        i = self._parse("was ist die hauptstadt von frankreich")
        assert i.type == "unknown"

    def test_empty_string(self):
        i = self._parse("")
        assert i.type == "unknown"
        assert i.confidence == 0.0

    # Intent dict
    def test_to_dict_structure(self):
        i = self._parse("lauter")
        d = i.to_dict()
        assert "type" in d
        assert "confidence" in d
        assert "params" in d

    @pytest.mark.parametrize("text,expected", [
        ("lauter",      "volume_up"),
        ("leiser",      "volume_down"),
        ("pause",       "pause"),
        ("nächstes",    "next"),
        ("zurück",      "prev"),
        ("hallo",       "greeting"),
        ("ich bin Max", "user_switch"),
    ])
    def test_parametrized_intents(self, text, expected):
        assert self._parse(text).type == expected


# ── Whisper STT ───────────────────────────────────────────────────────────────

class TestWhisperService:
    def test_setup_without_model_fails_gracefully(self):
        from services.ai.stt import WhisperService
        svc = WhisperService(model_name="nonexistent_model_xyz")
        result = svc.setup()
        assert isinstance(result, bool)
        # Either True (whisper installed) or False (not installed)

    def test_not_available_returns_none(self):
        from services.ai.stt import WhisperService
        svc = WhisperService()
        svc._available = False
        result = asyncio.run(svc.transcribe_file("/nonexistent.wav"))
        assert result is None

    def test_singleton(self):
        from services.ai.stt import get_stt_service
        assert get_stt_service() is get_stt_service()

    def test_model_name_accessible(self):
        from services.ai.stt import WhisperService
        svc = WhisperService(model_name="tiny")
        assert svc.model_name == "tiny"


# ── Piper TTS ─────────────────────────────────────────────────────────────────

class TestPiperTTS:
    def test_setup_without_binary_uses_fallback(self):
        from services.ai.tts import PiperTTSService
        svc = PiperTTSService()
        svc.setup()
        assert isinstance(svc.available, bool)

    def test_speak_mock_mode(self):
        """When neither piper nor espeak available, speak silently succeeds."""
        from services.ai.tts import PiperTTSService
        svc = PiperTTSService()
        svc._available = False
        svc._fallback  = False
        result = asyncio.run(svc.speak("Hallo Wundio"))
        assert result is True

    def test_speak_empty_string(self):
        from services.ai.tts import PiperTTSService
        svc = PiperTTSService()
        result = asyncio.run(svc.speak(""))
        assert result is True

    def test_set_voice_valid(self):
        from services.ai.tts import PiperTTSService, VOICES
        svc = PiperTTSService()
        first_voice = next(iter(VOICES))
        svc.set_voice(first_voice)
        assert svc._voice == first_voice

    def test_set_voice_invalid_ignored(self):
        from services.ai.tts import PiperTTSService
        svc = PiperTTSService()
        original = svc._voice
        svc.set_voice("nonexistent_voice")
        # Should not crash, voice unchanged
        assert svc._voice == original

    def test_list_voices(self):
        from services.ai.tts import PiperTTSService
        svc = PiperTTSService()
        voices = svc.list_voices()
        assert isinstance(voices, dict)
        assert len(voices) > 0

    def test_singleton(self):
        from services.ai.tts import get_tts_service
        assert get_tts_service() is get_tts_service()


# ── Wake-Word Service ─────────────────────────────────────────────────────────

class TestWakeWordService:
    def test_setup_returns_bool(self):
        from services.ai.wake import WakeWordService
        svc = WakeWordService()
        result = svc.setup(pi_generation=3)
        assert isinstance(result, bool)

    def test_set_phrase(self):
        from services.ai.wake import WakeWordService
        svc = WakeWordService(phrase="hey wundio")
        svc.set_phrase("hallo box")
        assert svc.phrase == "hallo box"

    def test_set_phrase_normalised(self):
        from services.ai.wake import WakeWordService
        svc = WakeWordService()
        svc.set_phrase("  HEY WUNDIO  ")
        assert svc.phrase == "hey wundio"

    def test_simulate_wake_calls_callback(self):
        from services.ai.wake import WakeWordService
        triggered = []
        async def run():
            svc = WakeWordService()
            svc.setup(pi_generation=4)
            async def cb(): triggered.append(True)
            svc.on_wake(cb)
            await svc.simulate_wake()
        asyncio.run(run())
        assert triggered

    def test_cooldown_prevents_double_trigger(self):
        from services.ai.wake import WakeWordService
        import time
        triggered = []
        async def run():
            svc = WakeWordService()
            svc.setup()
            svc._cooldown_s = 5.0   # 5s cooldown
            async def cb(): triggered.append(True)
            svc.on_wake(cb)
            await svc.simulate_wake()
            await svc.simulate_wake()   # should be blocked by cooldown
        asyncio.run(run())
        assert len(triggered) == 1

    def test_singleton(self):
        from services.ai.wake import get_wake_service
        assert get_wake_service() is get_wake_service()


# ── Voice Orchestrator ────────────────────────────────────────────────────────

class TestVoiceOrchestrator:
    def test_setup_returns_bool(self):
        from services.ai.voice import VoiceOrchestrator
        from services.ai.stt import WhisperService
        from services.ai.tts import PiperTTSService
        from services.ai.wake import WakeWordService
        orch = VoiceOrchestrator(
            stt=WhisperService(), tts=PiperTTSService(), wake=WakeWordService()
        )
        result = orch.setup(pi_generation=3)
        assert isinstance(result, bool)

    def test_handle_text_returns_intent(self):
        from services.ai.voice import VoiceOrchestrator
        from services.ai.stt import WhisperService
        from services.ai.tts import PiperTTSService
        from services.ai.wake import WakeWordService

        async def run():
            orch = VoiceOrchestrator(
                stt=WhisperService(), tts=PiperTTSService(), wake=WakeWordService()
            )
            orch.setup(pi_generation=4)
            intent = await orch.handle_text("lauter bitte")
            return intent

        intent = asyncio.run(run())
        assert intent.type == "volume_up"

    def test_handle_text_dispatches_callback(self):
        from services.ai.voice import VoiceOrchestrator
        from services.ai.stt import WhisperService
        from services.ai.tts import PiperTTSService
        from services.ai.wake import WakeWordService
        dispatched = []

        async def run():
            orch = VoiceOrchestrator(
                stt=WhisperService(), tts=PiperTTSService(), wake=WakeWordService()
            )
            orch.setup()
            async def on_action(intent): dispatched.append(intent)
            orch.on_action(on_action)
            await orch.handle_text("nächstes lied")

        asyncio.run(run())
        assert len(dispatched) == 1
        assert dispatched[0].type == "next"

    def test_singleton(self):
        from services.ai.voice import get_voice_orchestrator
        assert get_voice_orchestrator() is get_voice_orchestrator()


# ── Voice API ─────────────────────────────────────────────────────────────────

class TestVoiceApi:
    def test_status(self, api_client):
        r = api_client.get("/api/voice/status")
        assert r.status_code == 200
        d = r.json()
        for key in ("stt_available", "tts_available", "wake_available", "voice_enabled"):
            assert key in d

    def test_list_voices(self, api_client):
        r = api_client.get("/api/voice/voices")
        assert r.status_code == 200
        assert "voices" in r.json()
        assert len(r.json()["voices"]) > 0

    def test_parse_intent_volume_up(self, api_client):
        r = api_client.post("/api/voice/parse-intent", json={"text": "lauter"})
        assert r.status_code == 200
        assert r.json()["type"] == "volume_up"

    def test_parse_intent_greeting(self, api_client):
        r = api_client.post("/api/voice/parse-intent", json={"text": "hallo"})
        assert r.json()["type"] == "greeting"

    def test_parse_intent_unknown(self, api_client):
        r = api_client.post("/api/voice/parse-intent", json={"text": "was ist 42 mal 7"})
        assert r.json()["type"] == "unknown"

    def test_process_text(self, api_client):
        r = api_client.post("/api/voice/process", json={"text": "lauter bitte"})
        assert r.status_code == 200
        assert r.json()["type"] == "volume_up"

    def test_speak_endpoint(self, api_client):
        r = api_client.post("/api/voice/speak", json={"text": "Hallo Wundio"})
        assert r.status_code == 200
        assert r.json()["text"] == "Hallo Wundio"

    def test_simulate_wake(self, api_client):
        r = api_client.post("/api/voice/simulate-wake")
        assert r.status_code == 200

    def test_set_wake_phrase_valid(self, api_client):
        r = api_client.post("/api/voice/set-wake-phrase", json={"phrase": "hallo box"})
        assert r.status_code == 200
        assert r.json()["phrase"] == "hallo box"

    def test_set_wake_phrase_too_short(self, api_client):
        r = api_client.post("/api/voice/set-wake-phrase", json={"phrase": "hi"})
        assert r.status_code == 422

    def test_voice_config_enable(self, api_client):
        r = api_client.put("/api/voice/config", json={"enabled": True})
        assert r.status_code == 200
        from database import get_setting
        assert get_setting("voice_enabled") == "true"

    def test_voice_config_invalid_voice(self, api_client):
        r = api_client.put("/api/voice/config", json={"enabled": True, "tts_voice": "nonexistent"})
        assert r.status_code == 422

    @pytest.mark.parametrize("text,expected_type", [
        ("lauter",           "volume_up"),
        ("leiser",           "volume_down"),
        ("nächstes",         "next"),
        ("zurück",           "prev"),
        ("pause",            "pause"),
        ("hallo",            "greeting"),
        ("ich bin Lena",     "user_switch"),
        ("spiele kinderlieder", "play_playlist"),
    ])
    def test_parse_parametrized(self, api_client, text, expected_type):
        r = api_client.post("/api/voice/parse-intent", json={"text": text})
        assert r.json()["type"] == expected_type, f"'{text}' → got {r.json()['type']}"
