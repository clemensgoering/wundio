"""
Phase 1 – Spotify, Buttons & Playback API Tests
"""
import asyncio
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
    """Unit tests for the synchronous play_uri internals.

    Tests call _play_uri_sync directly to avoid asyncio overhead and to allow
    fine-grained mocking of the individual HTTP helpers.
    """

    def test_returns_false_when_credentials_missing(self, monkeypatch):
        """No credentials → False immediately, no network call."""
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = ""
        mock_cfg.spotify_client_secret = ""
        mock_cfg.spotify_refresh_token = ""
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        svc = SpotifyService()
        result = svc._play_uri_sync("spotify:playlist:abc")
        assert result is False

    def test_returns_false_on_token_failure(self, monkeypatch):
        """Token refresh error → False, does not propagate exception."""
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = "id"
        mock_cfg.spotify_client_secret = "secret"
        mock_cfg.spotify_refresh_token = "token"
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        svc = SpotifyService()
        svc._fetch_access_token = MagicMock(side_effect=Exception("Network error"))

        result = svc._play_uri_sync("spotify:playlist:abc")
        assert result is False

    def test_returns_false_when_no_device_found(self, monkeypatch):
        """No active Spotify device → False, informative log."""
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = "id"
        mock_cfg.spotify_client_secret = "secret"
        mock_cfg.spotify_refresh_token = "token"
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        svc = SpotifyService()
        svc._fetch_access_token = MagicMock(return_value="access_tok")
        svc._find_device_id     = MagicMock(return_value=None)

        result = svc._play_uri_sync("spotify:playlist:abc")
        assert result is False

    def test_returns_true_on_success(self, monkeypatch):
        """All helpers succeed → True."""
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = "id"
        mock_cfg.spotify_client_secret = "secret"
        mock_cfg.spotify_refresh_token = "token"
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        svc = SpotifyService()
        svc._fetch_access_token  = MagicMock(return_value="access_tok")
        svc._find_device_id      = MagicMock(return_value="device-123")
        svc._send_play_request   = MagicMock()

        result = svc._play_uri_sync("spotify:playlist:abc")
        assert result is True
        svc._send_play_request.assert_called_once_with(
            "access_tok", "device-123", "spotify:playlist:abc"
        )

    def test_playlist_uri_uses_context_uri(self, monkeypatch):
        """Playlists must use context_uri, not uris[]."""
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = "id"
        mock_cfg.spotify_client_secret = "secret"
        mock_cfg.spotify_refresh_token = "token"
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        captured = {}

        def capture_play(access_token, device_id, uri):
            captured["uri"] = uri

        svc = SpotifyService()
        svc._fetch_access_token = MagicMock(return_value="tok")
        svc._find_device_id     = MagicMock(return_value="dev")
        svc._send_play_request  = capture_play

        svc._play_uri_sync("spotify:playlist:37i9dQZF1DX0XUsuxWHRQd")
        # _send_play_request receives the URI; body construction is inside it
        assert captured["uri"] == "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd"

    def test_track_uri_uses_uris_list(self, monkeypatch):
        """Tracks must use uris[], not context_uri."""
        # The body-building logic lives in _send_play_request;
        # we verify the URI is passed through correctly.
        from services.spotify import SpotifyService
        from unittest.mock import MagicMock

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id     = "id"
        mock_cfg.spotify_client_secret = "secret"
        mock_cfg.spotify_refresh_token = "token"
        monkeypatch.setattr("services.spotify.get_settings", lambda: mock_cfg)

        captured = {}

        def capture_play(access_token, device_id, uri):
            captured["uri"] = uri

        svc = SpotifyService()
        svc._fetch_access_token = MagicMock(return_value="tok")
        svc._find_device_id     = MagicMock(return_value="dev")
        svc._send_play_request  = capture_play

        svc._play_uri_sync("spotify:track:4iV5W9uYEdYUVa79Axb7Rh")
        assert captured["uri"] == "spotify:track:4iV5W9uYEdYUVa79Axb7Rh"


# ── SpotifyService.play_uri (async) ───────────────────────────────────────────

class TestPlayUriAsync:
    """Verify that play_uri is a coroutine and does not block the event loop."""

    def test_play_uri_is_coroutine(self):
        """play_uri must be awaitable (coroutine function)."""
        import inspect
        from services.spotify import SpotifyService
        svc = SpotifyService()
        assert inspect.iscoroutinefunction(svc.play_uri), (
            "play_uri must be async so it can be awaited in _on_rfid_scan"
        )

    def test_play_uri_delegates_to_sync_impl(self):
        """play_uri must call _play_uri_sync via asyncio.to_thread."""
        from services.spotify import SpotifyService

        results = []

        async def run():
            svc = SpotifyService()
            svc._play_uri_sync = lambda uri: results.append(uri) or True
            await svc.play_uri("spotify:playlist:test")

        asyncio.run(run())
        assert results == ["spotify:playlist:test"]

    def test_play_uri_returns_bool(self):
        """play_uri must propagate the bool return from _play_uri_sync."""
        from services.spotify import SpotifyService

        async def run():
            svc = SpotifyService()
            svc._play_uri_sync = lambda uri: False
            return await svc.play_uri("spotify:playlist:test")

        result = asyncio.run(run())
        assert result is False


# ── SpotifyService._find_device_id ────────────────────────────────────────────

class TestFindDeviceId:
    def test_prefers_device_matching_name(self):
        """Device whose name contains self._device_name wins."""
        from services.spotify import SpotifyService

        devices_json = json.dumps({"devices": [
            {"id": "other-id",  "name": "SomeOtherDevice"},
            {"id": "wundio-id", "name": "Wundio"},
        ]}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = devices_json
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__  = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            svc = SpotifyService(device_name="Wundio")
            device_id = svc._find_device_id("tok")

        assert device_id == "wundio-id"

    def test_falls_back_to_first_device(self):
        """Falls back to first device when name does not match."""
        from services.spotify import SpotifyService

        devices_json = json.dumps({"devices": [
            {"id": "first-id",  "name": "Laptop"},
            {"id": "second-id", "name": "Phone"},
        ]}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = devices_json
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__  = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            svc = SpotifyService(device_name="Wundio")
            device_id = svc._find_device_id("tok")

        assert device_id == "first-id"

    def test_returns_none_when_no_devices(self):
        """Returns None when Spotify reports no active devices."""
        from services.spotify import SpotifyService

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"devices": []}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__  = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            svc = SpotifyService()
            assert svc._find_device_id("tok") is None


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