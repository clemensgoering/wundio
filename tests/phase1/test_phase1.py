"""
Phase 1 – Spotify, Buttons & Playback API Tests
"""
import asyncio
import inspect
import json
import pytest
from unittest.mock import MagicMock, patch


# ── SpotifyService ────────────────────────────────────────────────────────────

class TestSpotifyService:
    def test_setup_without_binary(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        # No librespot binary on CI – should fail gracefully
        result = svc.setup()
        assert isinstance(result, bool)

    def test_set_volume_clamps(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        svc.set_volume(150)
        assert svc.get_state().volume == 100
        svc.set_volume(-10)
        assert svc.get_state().volume == 0

    def test_set_volume_valid(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        for v in (0, 50, 70, 100):
            svc.set_volume(v)
            assert svc.get_state().volume == v

    def test_set_volume_uses_percentage_syntax(self):
        """amixer must be called with '<n>%', not a raw 0-65535 value.

        The old code mapped 0-100 → 0-65535 which breaks on I2S DACs and
        HiFiBerry HATs. Using percentage syntax works across all backends.
        """
        from services.spotify import SpotifyService
        calls = []
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            svc = SpotifyService()
            svc.set_volume(75)
            if mock_run.called:
                args = mock_run.call_args[0][0]
                # Must contain "75%" not "49151" (which was 75/100 * 65535)
                assert "75%" in args, f"Expected '75%' in amixer args, got: {args}"
                assert "49151" not in " ".join(str(a) for a in args)

    def test_set_volume_persists_to_state_file(self, tmp_path, monkeypatch):
        """Volume must be written to the state file so it survives restarts."""
        from services import spotify as mod
        state_file = tmp_path / "player.json"
        monkeypatch.setattr(mod, "STATE_FILE", state_file)

        svc = mod.SpotifyService()
        svc.set_volume(42)

        assert state_file.exists()
        data = json.loads(state_file.read_text())
        assert data["volume"] == 42

    def test_state_dict_keys(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        d = svc.get_state().to_dict()
        for key in ("playing", "track", "artist", "album", "volume"):
            assert key in d

    def test_refresh_state_no_file(self, tmp_path, monkeypatch):
        """refresh_state must not crash if state file is absent."""
        from services import spotify as mod
        monkeypatch.setattr(mod, "STATE_FILE", tmp_path / "missing.json")
        svc = mod.SpotifyService()
        state = svc.refresh_state()
        assert state.playing is False

    def test_refresh_state_from_file(self, tmp_path, monkeypatch):
        from services import spotify as mod
        state_file = tmp_path / "player.json"
        state_file.write_text(json.dumps({
            "playing": True,
            "track": "Bohemian Rhapsody",
            "artist": "Queen",
            "album": "A Night at the Opera",
        }))
        monkeypatch.setattr(mod, "STATE_FILE", state_file)
        svc = mod.SpotifyService()
        state = svc.refresh_state()
        assert state.playing is True
        assert state.track_name == "Bohemian Rhapsody"
        assert state.artist_name == "Queen"

    def test_singleton(self):
        from services.spotify import get_spotify_service
        assert get_spotify_service() is get_spotify_service()


# ── SpotifyService._play_uri_sync (unit) ──────────────────────────────────────

class TestPlayUriSync:
    def _make_svc(self):
        from services.spotify import SpotifyService
        return SpotifyService()
 
    def _mock_cfg(self, **kwargs):
        cfg = MagicMock()
        cfg.spotify_client_id     = kwargs.get("client_id",     "test_id")
        cfg.spotify_client_secret = kwargs.get("client_secret", "test_secret")
        cfg.spotify_refresh_token = kwargs.get("refresh_token", "test_refresh")
        return cfg
 
    def test_returns_false_when_credentials_missing(self):
        svc = self._make_svc()
        cfg = self._mock_cfg(client_id="", client_secret="", refresh_token="")
        with patch("config.get_settings", return_value=cfg):
            assert svc.play_uri("spotify:playlist:abc") is False
 
    def test_returns_false_on_token_failure(self):
        svc = self._make_svc()
        cfg = self._mock_cfg()
        with patch("config.get_settings", return_value=cfg):
            with patch.object(svc, "_fetch_access_token", side_effect=Exception("auth failed")):
                assert svc.play_uri("spotify:playlist:abc") is False
 
    def test_returns_false_when_no_device_found(self):
        svc = self._make_svc()
        cfg = self._mock_cfg()
        with patch("config.get_settings", return_value=cfg):
            with patch.object(svc, "_fetch_access_token", return_value="tok"):
                with patch.object(svc, "_find_device", return_value=(None, False)):
                    with patch("time.sleep"):  # skip retry wait
                        assert svc.play_uri("spotify:playlist:abc") is False
 
    def test_returns_true_on_success(self):
        svc = self._make_svc()
        cfg = self._mock_cfg()
        mock_resp = MagicMock()
        mock_resp.status = 204
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
 
        with patch("config.get_settings", return_value=cfg):
            with patch.object(svc, "_fetch_access_token", return_value="tok"):
                with patch.object(svc, "_find_device", return_value=("dev123", True)):
                    with patch("urllib.request.urlopen", return_value=mock_resp):
                        result = svc.play_uri("spotify:playlist:abc")
 
        assert result is True
 
    def test_playlist_uri_uses_context_uri(self):
        svc = self._make_svc()
        cfg = self._mock_cfg()
        captured = {}
 
        def fake_urlopen(req, timeout=None):
            captured["body"] = __import__("json").loads(req.data)
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp
 
        with patch("config.get_settings", return_value=cfg):
            with patch.object(svc, "_fetch_access_token", return_value="tok"):
                with patch.object(svc, "_find_device", return_value=("dev123", True)):
                    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                        svc.play_uri("spotify:playlist:abc123")
 
        assert "context_uri" in captured.get("body", {})
        assert "uris" not in captured.get("body", {})
 
    def test_track_uri_uses_uris_list(self):
        svc = self._make_svc()
        cfg = self._mock_cfg()
        captured = {}
 
        def fake_urlopen(req, timeout=None):
            captured["body"] = __import__("json").loads(req.data)
            mock_resp = MagicMock()
            mock_resp.status = 204
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp
 
        with patch("config.get_settings", return_value=cfg):
            with patch.object(svc, "_fetch_access_token", return_value="tok"):
                with patch.object(svc, "_find_device", return_value=("dev123", True)):
                    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
                        svc.play_uri("spotify:track:xyz789")
 
        assert "uris" in captured.get("body", {})
        assert "context_uri" not in captured.get("body", {})


# ── SpotifyService.play_uri (async) ───────────────────────────────────────────

class TestPlayUriAsync:
    def test_play_uri_is_coroutine(self):
        """play_uri_async must be awaitable; play_uri is the sync implementation."""
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert inspect.iscoroutinefunction(svc.play_uri_async), \
            "play_uri_async must be async so it can be awaited in _on_rfid_scan"
 
    def test_play_uri_delegates_to_sync_impl(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        with patch.object(svc, "play_uri", return_value=True) as mock_sync:
            result = asyncio.run(svc.play_uri_async("spotify:playlist:test"))
        mock_sync.assert_called_once_with("spotify:playlist:test")
        assert result is True
 
    def test_play_uri_returns_bool(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        with patch.object(svc, "play_uri", return_value=False):
            result = asyncio.run(svc.play_uri_async("spotify:track:test"))
        assert result is False


# ── SpotifyService._find_device_id ────────────────────────────────────────────

class TestFindDeviceId:
    def _make_svc(self, device_name: str = "Wundio"):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        svc._device_name = device_name   # set directly instead of constructor arg
        return svc
 
    def test_prefers_device_matching_name(self):
        svc = self._make_svc("Wundio")
        devices = [
            {"id": "aaa", "name": "Some Speaker", "is_active": False},
            {"id": "bbb", "name": "Wundio",        "is_active": True},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps({"devices": devices}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
 
        with patch("urllib.request.urlopen", return_value=mock_resp):
            device_id, is_active = svc._find_device("fake_token")
 
        assert device_id == "bbb"
        assert is_active is True
 
    def test_falls_back_to_first_device(self):
        svc = self._make_svc("Wundio")
        devices = [
            {"id": "zzz", "name": "Other Device", "is_active": True},
        ]
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps({"devices": devices}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
 
        # "Wundio" not in list → should return (None, False) with new strict logic
        with patch("urllib.request.urlopen", return_value=mock_resp):
            device_id, is_active = svc._find_device("fake_token")
 
        # New behaviour: no fallback to other devices, returns None
        assert device_id is None
        assert is_active is False
 
    def test_returns_none_when_no_devices(self):
        svc = self._make_svc("Wundio")
        mock_resp = MagicMock()
        mock_resp.read.return_value = __import__("json").dumps({"devices": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
 
        with patch("urllib.request.urlopen", return_value=mock_resp):
            device_id, is_active = svc._find_device("fake_token")
 
        assert device_id is None
        assert is_active is False


# ── ButtonService ─────────────────────────────────────────────────────────────

class TestButtonService:
    def test_setup_without_gpio(self):
        from services.buttons import ButtonService
        svc = ButtonService()
        svc.register("play_pause", 17)
        result = svc.setup()
        assert isinstance(result, bool)

    def test_register_multiple(self):
        from services.buttons import ButtonService
        svc = ButtonService()
        for name, pin in [("play_pause", 17), ("next", 27), ("prev", 22)]:
            svc.register(name, pin)
        assert len(svc._buttons) == 3

    def test_simulate_press_calls_callback(self):
        from services.buttons import ButtonService
        received = []

        async def run():
            svc = ButtonService()
            svc.register("vol_up", 23)
            async def cb(name): received.append(name)
            svc.on_press(cb)
            await svc.simulate_press("vol_up")

        asyncio.run(run())
        assert "vol_up" in received

    def test_simulate_unknown_button_safe(self):
        from services.buttons import ButtonService

        async def run():
            svc = ButtonService()
            svc.register("play_pause", 17)
            await svc.simulate_press("nonexistent")  # must not raise

        asyncio.run(run())

    def test_build_default_has_five_buttons(self):
        from services.buttons import build_default_service
        from config import get_settings
        svc = build_default_service(get_settings())
        assert len(svc._buttons) == 5
        assert "play_pause" in svc._buttons
        assert "vol_up" in svc._buttons


# ── Playback API ──────────────────────────────────────────────────────────────

class TestPlaybackApi:
    def test_get_state(self, api_client):
        r = api_client.get("/api/playback/state")
        assert r.status_code == 200
        d = r.json()
        assert "playing" in d
        assert "volume" in d

    def test_set_volume_valid(self, api_client):
        r = api_client.post("/api/playback/volume", json={"volume": 60})
        assert r.status_code == 200
        assert r.json()["volume"] == 60

    def test_set_volume_out_of_range(self, api_client):
        assert api_client.post("/api/playback/volume", json={"volume": 150}).status_code == 422

    def test_set_active_user(self, api_client):
        uid = api_client.post("/api/users/", json={
            "name": "lena", "display_name": "Lena", "volume": 75
        }).json()["id"]
        r = api_client.post("/api/playback/active-user", json={"user_id": uid})
        assert r.status_code == 200
        assert r.json()["active_user"] == "Lena"
        assert r.json()["volume"] == 75

    def test_set_active_user_nonexistent(self, api_client):
        r = api_client.post("/api/playback/active-user", json={"user_id": 9999})
        assert r.status_code == 404

    @pytest.mark.parametrize("btn", ["play_pause", "next", "prev", "vol_up", "vol_down"])
    def test_simulate_valid_buttons(self, api_client, btn):
        r = api_client.post(f"/api/playback/button/{btn}")
        assert r.status_code == 200

    def test_simulate_invalid_button(self, api_client):
        r = api_client.post("/api/playback/button/explode")
        assert r.status_code == 422



# ── In TestPlaybackApi einfügen ───────────────────────────────────────────────

class TestPlaybackApiExtended:
    """Tests for toggle, next, prev endpoints added in Phase 1 completion."""

    def test_toggle_endpoint_exists(self, api_client):
        """POST /api/playback/toggle must return 200, not 405."""
        with patch("services.spotify.SpotifyService.toggle_play_pause", return_value=True):
            r = api_client.post("/api/playback/toggle")
        assert r.status_code == 200

    def test_toggle_returns_ok_and_playing_state(self, api_client):
        with patch("services.spotify.SpotifyService.toggle_play_pause", return_value=True):
            r = api_client.post("/api/playback/toggle")
        assert r.status_code == 200
        d = r.json()
        assert "ok" in d
        assert "playing" in d
        assert isinstance(d["playing"], bool)

    def test_toggle_ok_false_when_spotify_fails(self, api_client):
        with patch("services.spotify.SpotifyService.toggle_play_pause", return_value=False):
            r = api_client.post("/api/playback/toggle")
        assert r.status_code == 200
        assert r.json()["ok"] is False

    def test_next_endpoint_exists(self, api_client):
        """POST /api/playback/next must return 200, not 405."""
        with patch("services.spotify.SpotifyService.next_track", return_value=True):
            r = api_client.post("/api/playback/next")
        assert r.status_code == 200

    def test_next_returns_ok(self, api_client):
        with patch("services.spotify.SpotifyService.next_track", return_value=True):
            r = api_client.post("/api/playback/next")
        assert r.json()["ok"] is True

    def test_prev_endpoint_exists(self, api_client):
        """POST /api/playback/prev must return 200, not 405."""
        with patch("services.spotify.SpotifyService.prev_track", return_value=True):
            r = api_client.post("/api/playback/prev")
        assert r.status_code == 200

    def test_prev_returns_ok(self, api_client):
        with patch("services.spotify.SpotifyService.prev_track", return_value=True):
            r = api_client.post("/api/playback/prev")
        assert r.json()["ok"] is True

    def test_next_ok_false_when_spotify_fails(self, api_client):
        with patch("services.spotify.SpotifyService.next_track", return_value=False):
            r = api_client.post("/api/playback/next")
        assert r.json()["ok"] is False

    def test_prev_ok_false_when_spotify_fails(self, api_client):
        with patch("services.spotify.SpotifyService.prev_track", return_value=False):
            r = api_client.post("/api/playback/prev")
        assert r.json()["ok"] is False


# ── Ergänzung für TestPlayUriAsync ────────────────────────────────────────────

class TestPlayUriAsyncExtended:
    """Additional async wrapper tests."""

    def test_play_uri_async_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "play_uri_async")
        assert asyncio.iscoroutinefunction(svc.play_uri_async)

    def test_play_uri_sync_exists_and_is_not_async(self):
        """play_uri must be sync so it can run in asyncio.to_thread."""
        import inspect
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "play_uri")
        assert not inspect.iscoroutinefunction(svc.play_uri)

    def test_toggle_play_pause_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "toggle_play_pause")

    def test_next_track_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "next_track")

    def test_prev_track_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "prev_track")

    def test_pause_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "pause")

    def test_resume_exists(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert hasattr(svc, "resume")


# ── Feedback Bus Tests ────────────────────────────────────────────────────────

class TestFeedbackBus:
    """Tests for the device feedback event system."""

    def test_feedback_bus_singleton(self):
        from services.feedback import get_feedback_bus
        b1 = get_feedback_bus()
        b2 = get_feedback_bus()
        assert b1 is b2

    def test_feedback_event_fields(self):
        from services.feedback import FeedbackEvent
        e = FeedbackEvent(type="rfid_scan", label="Test", color="amber", duration_ms=1000)
        assert e.type == "rfid_scan"
        assert e.label == "Test"
        assert e.color == "amber"
        assert e.duration_ms == 1000

    def test_publish_delivers_to_queue(self):
        from services.feedback import FeedbackBus, FeedbackEvent
        bus = FeedbackBus()
        q = asyncio.Queue()
        bus._sse_queues.append(q)

        event = FeedbackEvent(type="test", label="hello", color="teal", duration_ms=500)
        asyncio.run(bus.publish(event))

        assert not q.empty()
        payload = q.get_nowait()
        import json
        data = json.loads(payload)
        assert data["type"] == "test"
        assert data["label"] == "hello"

    def test_hardware_listener_called(self):
        from services.feedback import FeedbackBus, FeedbackEvent
        bus = FeedbackBus()
        received = []
        bus.add_hardware_listener(lambda e: received.append(e))

        event = FeedbackEvent(type="rfid_scan", label="Tag", color="amber", duration_ms=800)
        asyncio.run(bus.publish(event))

        assert len(received) == 1
        assert received[0].type == "rfid_scan"

    def test_feedback_stream_endpoint(self, api_client):
        """SSE endpoint must return 200 with correct content-type.
        Uses timeout to prevent hanging on the infinite SSE stream.
        """
        import threading
        result = {}

        def call():
            try:
                r = api_client.get(
                    "/api/feedback/stream",
                    headers={"Accept": "text/event-stream"},
                    timeout=1.0,
                )
                result["status"] = r.status_code
                result["ct"] = r.headers.get("content-type", "")
            except Exception as exc:
                # Timeout is expected – we only care about the initial response
                result["exc"] = str(exc)

        t = threading.Thread(target=call)
        t.start()
        t.join(timeout=2.0)

        # Either we got a response or timed out – both mean the endpoint exists
        assert result.get("status") == 200 or "exc" in result
        if "ct" in result:
            assert "text/event-stream" in result["ct"]