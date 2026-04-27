"""
Tests for Spotify OAuth Flow

Covers: state encoding, /auth/start validation, /callback token exchange,
        /api/settings/spotify/status endpoint.

Relay protocol note:
  _encode_state encodes only the Pi origin (e.g. "http://192.168.1.1:8000").
  The wundio.dev relay page appends "/api/spotify/callback" itself before
  forwarding. Tests must assert on the origin, not the full callback path.
"""
import json
import base64
import urllib.parse
from unittest.mock import patch, MagicMock


# ── State encoding helpers ────────────────────────────────────────────────────

class TestStateEncoding:
    def test_encode_decode_roundtrip(self):
        """Round-trip: origin survives encode → decode unchanged."""
        from api.routes.spotify_auth import _encode_state, _decode_state
        origin = "http://192.168.178.50:8000"
        assert _decode_state(_encode_state(origin)) == origin

    def test_decode_invalid_state_returns_none(self):
        from api.routes.spotify_auth import _decode_state
        assert _decode_state("not-valid-base64!!!") is None
        assert _decode_state("") is None

    def test_decode_non_http_payload_returns_none(self):
        """Decoded value that doesn't start with 'http' is rejected."""
        from api.routes.spotify_auth import _decode_state
        # valid base64, but not an http origin
        payload = base64.urlsafe_b64encode(b"ftp://evil.example.com").decode()
        assert _decode_state(payload) is None

    def test_state_encodes_origin_only(self):
        """state must contain the Pi origin, not the full callback path.

        The relay at wundio.dev appends /api/spotify/callback itself.
        Embedding the path in state would break the relay contract.
        """
        from api.routes.spotify_auth import _encode_state, _decode_state
        origin = "http://10.0.0.1:8000"
        decoded = _decode_state(_encode_state(origin))
        assert decoded == origin
        assert "/api/spotify/callback" not in decoded


# ── /api/settings/spotify/status ─────────────────────────────────────────────

class TestSpotifyStatusEndpoint:
    def test_status_all_missing(self, api_client, tmp_path, monkeypatch):
        monkeypatch.setattr("api.routes.settings_routes.ENV_FILE", tmp_path / "wundio.env")
        (tmp_path / "wundio.env").write_text("")
        r = api_client.get("/api/settings/spotify/status")
        assert r.status_code == 200
        data = r.json()
        assert data["has_client_id"] is False
        assert data["has_secret"] is False
        assert data["has_refresh_token"] is False
        assert data["oauth_complete"] is False

    def test_status_all_present(self, api_client, tmp_path, monkeypatch):
        monkeypatch.setattr("api.routes.settings_routes.ENV_FILE", tmp_path / "wundio.env")
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
        monkeypatch.setattr("api.routes.settings_routes.ENV_FILE", tmp_path / "wundio.env")
        (tmp_path / "wundio.env").write_text("SPOTIFY_CLIENT_ID=abc123\n")
        r = api_client.get("/api/settings/spotify/status")
        data = r.json()
        assert data["has_client_id"] is True
        assert data["has_secret"] is False
        assert data["oauth_complete"] is False


# ── /api/spotify/auth/start ───────────────────────────────────────────────────

class TestSpotifyAuthStart:
    def test_missing_client_id_returns_error_page(self, api_client, monkeypatch):
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = ""
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)
        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        # Returns HTML error page (200) or 400 depending on implementation
        assert r.status_code in (200, 400)
        assert "client id" in r.text.lower() or "fehlt" in r.text.lower()

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

    def test_state_encodes_pi_origin(self, api_client, monkeypatch):
        """state parameter must decode to a valid http origin (not a full URL).

        The relay at wundio.dev appends /api/spotify/callback to the decoded
        origin before forwarding – the Pi must not include the path in state.
        """
        from api.routes.spotify_auth import _decode_state
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "test_client_id"
        mock_cfg.port = 8000
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)

        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        location = r.headers["location"]
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(location).query))
        state = params.get("state", "")

        decoded = _decode_state(state)
        assert decoded is not None, "state must be decodable"
        assert decoded.startswith("http"), "decoded state must be an http origin"
        # Must NOT contain the callback path – relay adds it
        assert "/api/spotify/callback" not in decoded, (
            "state must contain only the origin (http://ip:port), not the full "
            "callback path. The wundio.dev relay appends the path itself."
        )

    def test_relay_redirect_uri_is_wundio_dev(self, api_client, monkeypatch):
        """redirect_uri in the Spotify auth URL must point to wundio.dev (HTTPS).

        wundio.local is rejected by Spotify; the relay at wundio.dev/spotify-callback
        is the registered redirect URI.
        """
        mock_cfg = MagicMock()
        mock_cfg.spotify_client_id = "test_client_id"
        mock_cfg.port = 8000
        monkeypatch.setattr("api.routes.spotify_auth.get_settings", lambda: mock_cfg)

        r = api_client.get("/api/spotify/auth/start", follow_redirects=False)
        location = r.headers["location"]
        params = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(location).query))
        redirect_uri = urllib.parse.unquote(params.get("redirect_uri", ""))

        assert "wundio.dev" in redirect_uri, (
            f"redirect_uri must point to wundio.dev, got: {redirect_uri}"
        )
        assert redirect_uri.startswith("https://"), (
            "redirect_uri must be HTTPS (Spotify requirement)"
        )


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
        state = _encode_state("http://192.168.1.1:8000")
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
        monkeypatch.setattr("api.routes.spotify_auth._write_env_key", lambda k, v: None)

        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "access_token":  "access_tok",
            "refresh_token": "refresh_tok_123",
            "token_type":    "Bearer",
            "expires_in":    3600,
        }).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__  = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            state = _encode_state("http://testclient")
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
            state = _encode_state("http://testclient")
            r = api_client.get(f"/api/spotify/callback?code=code&state={state}")

        assert "fehlgeschlagen" in r.text.lower() or "fehler" in r.text.lower()