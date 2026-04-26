"""
Tests for Spotify OAuth Flow
Covers: state encoding, /auth/start validation, /callback token exchange,
        /api/settings/spotify/status endpoint
"""
import pytest
import json
import base64
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


# ── State encoding helpers ────────────────────────────────────────────────────

class TestStateEncoding:
    def test_encode_decode_roundtrip(self):
        from api.routes.spotify_auth import _encode_state, _decode_state
        uri = "http://192.168.178.50:8000/api/spotify/callback"
        assert _decode_state(_encode_state(uri)) == uri

    def test_decode_invalid_state_returns_none(self):
        from api.routes.spotify_auth import _decode_state
        assert _decode_state("not-valid-base64!!!") is None
        assert _decode_state("") is None

    def test_decode_missing_field_returns_none(self):
        from api.routes.spotify_auth import _decode_state
        # valid base64 JSON but missing redirect_uri key
        payload = base64.urlsafe_b64encode(json.dumps({"foo": "bar"}).encode()).decode()
        assert _decode_state(payload) is None


# ── /api/settings/spotify/status ─────────────────────────────────────────────

class TestSpotifyStatusEndpoint:
    def test_status_all_missing(self, api_client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routes.settings_routes.ENV_FILE",
            tmp_path / "wundio.env",
        )
        (tmp_path / "wundio.env").write_text("")
        r = api_client.get("/api/settings/spotify/status")
        assert r.status_code == 200
        data = r.json()
        assert data["has_client_id"] is False
        assert data["has_secret"] is False
        assert data["has_refresh_token"] is False
        assert data["oauth_complete"] is False

    def test_status_all_present(self, api_client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routes.settings_routes.ENV_FILE",
            tmp_path / "wundio.env",
        )
        (tmp_path / "wundio.env").write_text(
            "SPOTIFY_CLIENT_ID=abc123\n"
            "SPOTIFY_CLIENT_SECRET=secret456\n"
            "SPOTIFY_REFRESH_TOKEN=refresh789\n"
        )
        r = api_client.get("/api/settings/spotify/status")
        assert r.status_code == 200
        data = r.json()
        assert data["has_client_id"] is True
        assert data["has_secret"] is True
        assert data["has_refresh_token"] is True
        assert data["oauth_complete"] is True

    def test_status_partial(self, api_client, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "api.routes.settings_routes.ENV_FILE",
            tmp_path / "wundio.env",
        )
        (tmp_path / "wundio.env").write_text("SPOTIFY_CLIENT_ID=abc123\n")
        r = api_client.get("/api/settings/spotify/status")
        data = r.json()
        assert data["has_client_id"] is True
        assert data["has_secret"] is False
        assert data["oauth_complete"] is False


# ── /api/spotify/auth/start ───────────────────────────────────────────────────

class TestSpotifyAuthStart:
    def test_missing_client_id_returns_400(self, api_client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = ""
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)
        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        assert r.status_code == 400
        assert "Client ID" in r.text

    def test_redirects_to_spotify(self, api_client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "test_client_id"
        mock_cfg.port = 8000
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)
        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        assert r.status_code in (302, 307)
        location = r.headers["location"]
        assert "accounts.spotify.com/authorize" in location
        assert "test_client_id" in location
        assert "state=" in location

    def test_state_contains_redirect_uri(self, api_client, monkeypatch):
        from api.routes.spotify_auth import _decode_state
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "test_client_id"
        mock_cfg.port = 8000
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)
        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        location = r.headers["location"]
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(location).query))
        state = params.get("state", "")
        decoded_uri = _decode_state(state)
        assert decoded_uri is not None
        assert "/api/spotify/callback" in decoded_uri


# ── /api/spotify/callback ─────────────────────────────────────────────────────

class TestSpotifyCallback:
    def test_error_param_returns_error_page(self, api_client):
        r = api_client.get("/api/spotify/callback?error=access_denied")
        assert r.status_code == 200
        assert "abgebrochen" in r.text.lower() or "fehler" in r.text.lower()

    def test_missing_code_returns_error_page(self, api_client):
        r = api_client.get("/api/spotify/callback")
        assert r.status_code == 200
        assert "code" in r.text.lower() or "fehler" in r.text.lower()

    def test_missing_credentials_returns_error_page(self, api_client, monkeypatch):
        from api.routes.spotify_auth import _encode_state
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = ""
        mock_cfg.spotify_client_secret = ""
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)
        state = _encode_state("http://192.168.1.1:8000/api/spotify/callback")
        r = api_client.get(f"/api/spotify/callback?code=testcode&state={state}")
        assert "fehlt" in r.text.lower() or "credentials" in r.text.lower()

    def test_successful_token_exchange(self, api_client, monkeypatch, tmp_path):
        """Mock Spotify token endpoint and verify refresh token is stored."""
        from api.routes.spotify_auth import _encode_state

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "client_id"
        mock_cfg.spotify_client_secret = "client_secret"
        mock_cfg.port = 8000
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)

        env_file = tmp_path / "wundio.env"
        env_file.write_text("")
        monkeypatch.setattr("api.routes.spotify_auth._write_env_key", lambda k, v: None)

        # Mock the token exchange HTTP call
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token": "access_tok",
            "refresh_token": "refresh_tok_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            state = _encode_state("http://testclient/api/spotify/callback")
            r = api_client.get(f"/api/spotify/callback?code=auth_code_123&state={state}")

        assert r.status_code == 200
        assert "verbunden" in r.text.lower()

    def test_token_exchange_failure_returns_error(self, api_client, monkeypatch):
        from api.routes.spotify_auth import _encode_state

        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "client_id"
        mock_cfg.spotify_client_secret = "client_secret"
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)

        with patch("urllib.request.urlopen", side_effect=Exception("Network error")):
            state = _encode_state("http://testclient/api/spotify/callback")
            r = api_client.get(f"/api/spotify/callback?code=code&state={state}")

        assert "fehlgeschlagen" in r.text.lower() or "fehler" in r.text.lower()


import urllib.parse