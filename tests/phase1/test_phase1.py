"""
Phase 1 – Spotify (go-librespot), Buttons & Playback API Tests
"""
import asyncio
import inspect
import json
import pytest
from unittest.mock import MagicMock, patch


def _running_svc():
    """SpotifyService that believes go-librespot is running (API calls mocked per test)."""
    from services.spotify import SpotifyService
    svc = SpotifyService()
    svc._available = True
    svc._process = MagicMock(returncode=None)
    return svc


def _api_router(routes: dict):
    """Fake SpotifyService._api: maps (method, path) → (status, body), records calls."""
    calls = []

    def fake(method, path, body=None, timeout=5):
        calls.append((method, path, body))
        return routes.get((method, path), (0, None))

    return fake, calls


# ── SpotifyService ────────────────────────────────────────────────────────────

class TestSpotifyService:
    def test_setup_without_binary(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        # No go-librespot binary on CI – should fail gracefully
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
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            svc = SpotifyService()
            svc.set_volume(75)
            args = mock_run.call_args[0][0]
            assert "75%" in args, f"Expected '75%' in amixer args, got: {args}"
            assert "49151" not in " ".join(str(a) for a in args)

    def test_set_volume_primes_softvol_when_master_missing(self):
        """softvol 'Master' only exists after first playback – prime and retry."""
        from services.spotify import SpotifyService
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            SpotifyService().set_volume(40)
        cmds = [c[0][0][0] for c in mock_run.call_args_list]
        assert cmds == ["amixer", "aplay", "amixer"]

    def test_state_dict_keys(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        d = svc.get_state().to_dict()
        for key in ("playing", "track", "artist", "album", "volume", "context_uri"):
            assert key in d

    def test_api_not_called_when_daemon_not_running(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        with patch("urllib.request.urlopen") as mock_open:
            assert svc._api("GET", "/status") == (0, None)
            assert svc.play_uri("spotify:album:x") is False
        mock_open.assert_not_called()

    def test_refresh_state_daemon_down_keeps_defaults(self):
        from services.spotify import SpotifyService
        state = SpotifyService().refresh_state()
        assert state.playing is False

    def test_refresh_state_from_status(self):
        svc = _running_svc()
        fake, _ = _api_router({("GET", "/status"): (200, {
            "stopped": False, "paused": False,
            "context_uri": "spotify:album:abc",
            "track": {
                "uri": "spotify:track:1", "name": "Bohemian Rhapsody",
                "artist_names": ["Queen"], "album_name": "A Night at the Opera",
                "position": 1000, "duration": 354000,
            },
        })})
        with patch.object(svc, "_api", side_effect=fake):
            state = svc.refresh_state()
        assert state.playing is True
        assert state.track_name == "Bohemian Rhapsody"
        assert state.artist_name == "Queen"
        assert state.context_uri == "spotify:album:abc"

    def test_refresh_state_paused(self):
        svc = _running_svc()
        fake, _ = _api_router({("GET", "/status"): (200, {"paused": True, "stopped": False, "track": None})})
        with patch.object(svc, "_api", side_effect=fake):
            assert svc.refresh_state().playing is False

    def test_singleton(self):
        from services.spotify import get_spotify_service
        assert get_spotify_service() is get_spotify_service()


# ── go-librespot config ───────────────────────────────────────────────────────

class TestGoLibrespotConfig:
    def test_config_uses_device_auth_and_local_api(self, tmp_path):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        svc._config_dir = tmp_path
        svc.write_config()
        cfg = json.loads((tmp_path / "config.yml").read_text())
        assert cfg["credentials"] == {"type": "device_auth"}
        assert cfg["server"]["enabled"] is True
        assert cfg["server"]["address"] == "127.0.0.1"
        assert cfg["device_name"] == svc._device_name


# ── Playback via local API ────────────────────────────────────────────────────

class TestPlayUri:
    def test_posts_uri_to_local_api(self):
        svc = _running_svc()
        fake, calls = _api_router({("POST", "/player/play"): (200, None)})
        with patch.object(svc, "_api", side_effect=fake):
            assert svc.play_uri("spotify:playlist:abc") is True
        assert calls == [("POST", "/player/play", {"uri": "spotify:playlist:abc"})]

    def test_returns_false_when_rejected(self):
        svc = _running_svc()
        fake, _ = _api_router({("POST", "/player/play"): (500, None)})
        with patch.object(svc, "_api", side_effect=fake):
            assert svc.play_uri("spotify:track:xyz") is False

    def test_play_uri_async_is_coroutine(self):
        from services.spotify import SpotifyService
        assert inspect.iscoroutinefunction(SpotifyService().play_uri_async)

    def test_play_uri_async_delegates(self):
        from services.spotify import SpotifyService
        svc = SpotifyService()
        with patch.object(svc, "play_uri", return_value=True) as mock_sync:
            assert asyncio.run(svc.play_uri_async("spotify:playlist:test")) is True
        mock_sync.assert_called_once_with("spotify:playlist:test")

    @pytest.mark.parametrize("method,path", [
        ("pause", "/player/pause"),
        ("resume", "/player/resume"),
        ("next_track", "/player/next"),
        ("prev_track", "/player/prev"),
        ("toggle_play_pause", "/player/playpause"),
    ])
    def test_controls_hit_local_endpoints(self, method, path):
        svc = _running_svc()
        fake, calls = _api_router({("POST", path): (200, None)})
        with patch.object(svc, "_api", side_effect=fake):
            assert getattr(svc, method)() is True
        assert calls[0][:2] == ("POST", path)


# ── Login / pairing status ────────────────────────────────────────────────────

class TestStatusInfo:
    def test_not_running(self):
        from services.spotify import SpotifyService
        info = SpotifyService().status_info()
        assert info["running"] is False
        assert info["logged_in"] is False
        assert info["pairing"] is None

    def test_waiting_for_pairing(self):
        svc = _running_svc()
        fake, _ = _api_router({
            ("GET", "/"): (200, {"playback_ready": False}),
            ("GET", "/status"): (204, None),
            ("GET", "/auth/code"): (200, {
                "url": "https://spotify.com/pair?code=ABCD", "code": "ABCD",
                "expires_at": "2026-10-27T12:00:00Z",
            }),
        })
        with patch.object(svc, "_api", side_effect=fake):
            info = svc.status_info()
        assert info["logged_in"] is False
        assert info["pairing"]["code"] == "ABCD"

    def test_logged_in(self):
        svc = _running_svc()
        fake, calls = _api_router({
            ("GET", "/"): (200, {"playback_ready": True}),
            ("GET", "/status"): (200, {"username": "wundio-box", "device_name": "Wundio"}),
        })
        with patch.object(svc, "_api", side_effect=fake):
            info = svc.status_info()
        assert info["logged_in"] is True
        assert info["username"] == "wundio-box"
        assert info["playback_ready"] is True
        assert ("GET", "/auth/code", None) not in calls

    def test_logout_removes_credentials_and_restarts(self, tmp_path):
        svc = _running_svc()
        svc._config_dir = tmp_path
        (tmp_path / "state.json").write_text("{}")

        async def run():
            with patch.object(svc, "start") as mock_start, patch("asyncio.sleep"):
                mock_start.return_value = None
                ok = await svc.logout()
            return ok, mock_start

        ok, mock_start = asyncio.run(run())
        assert ok is True
        assert not (tmp_path / "state.json").exists()
        mock_start.assert_called_once()


# ── /api/spotify routes ───────────────────────────────────────────────────────

class TestSpotifyRoutes:
    def test_status_endpoint_shape(self, api_client):
        r = api_client.get("/api/spotify/status")
        assert r.status_code == 200
        d = r.json()
        for key in ("installed", "running", "logged_in", "username",
                    "device_name", "playback_ready", "pairing"):
            assert key in d

    def test_old_oauth_routes_removed(self, api_client):
        assert api_client.get("/api/spotify/auth/start", follow_redirects=False).status_code == 404
        assert api_client.get("/api/spotify/callback?code=x").status_code == 404

    def test_services_status_uses_local_player(self, api_client):
        r = api_client.get("/api/system/services")
        assert r.status_code == 200
        d = r.json()
        assert "wundio-spotify" in d["services"]
        assert set(d["spotify_device"]) == {"found", "name", "is_active", "error"}


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

    def test_feedback_stream_route_registered(self, api_client):
        """SSE route must be registered in the app – check via OpenAPI schema."""
        r = api_client.get("/openapi.json")
        assert r.status_code == 200
        paths = r.json().get("paths", {})
        assert "/api/feedback/stream" in paths, (
            "GET /api/feedback/stream not found in OpenAPI schema – route not registered"
        )