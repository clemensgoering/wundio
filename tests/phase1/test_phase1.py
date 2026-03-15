"""
Phase 1 – Spotify, Buttons & Playback API Tests
"""
import pytest
import asyncio


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
        import json
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
        # Create a user first
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
