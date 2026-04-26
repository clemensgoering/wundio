"""
Wundio – Spotify OAuth Flow (Decentralized)

Every user creates their own Spotify Developer App.
No central Wundio app → no single point of failure.

Flow:
  1. User visits wundio.dev/docs/spotify-setup (guided setup)
  2. Creates Spotify App with redirect URI: http://{BOX_IP}:8000/api/spotify/callback
  3. Scans QR code → GET /api/spotify/setup?client_id=...&secret=...
  4. Credentials stored in wundio.env
  5. User clicks "Mit Spotify verbinden" in Settings
  6. OAuth flow via /api/spotify/auth/start → /callback
  7. Refresh token stored
"""
import urllib.parse
import urllib.request
import base64
import json
import logging

from fastapi import APIRouter, Query
from fastapi.responses import RedirectResponse, HTMLResponse

from config import get_settings
from database import log_event

logger = logging.getLogger(__name__)
router = APIRouter(tags=["spotify-auth"])

SPOTIFY_SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
])


def _get_local_ip() -> str:
    """Get wlan0 IP for building redirect URI."""
    import subprocess
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=2
        )
        for line in result.stdout.splitlines():
            if "inet " in line:
                return line.split()[1].split('/')[0]
    except Exception:
        pass
    return "192.168.1.1"


def _get_redirect_uri() -> str:
    """Build callback URI using actual local IP."""
    cfg = get_settings()
    local_ip = _get_local_ip()
    return f"http://{local_ip}:{cfg.port}/api/spotify/callback"


def _write_env_key(key: str, value: str) -> None:
    """Write a single key to wundio.env."""
    from pathlib import Path
    env_file = Path("/etc/wundio/wundio.env")
    if not env_file.exists():
        logger.warning("wundio.env not found – cannot persist")
        return
    lines = env_file.read_text().splitlines()
    found = False
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            new_lines.append(f"{key}={value}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"{key}={value}")
    env_file.write_text("\n".join(new_lines) + "\n")


@router.get("/setup")
async def spotify_setup(
    client_id: str = Query(..., min_length=10),
    secret: str = Query(..., min_length=10)
):
    """
    QR-Scan endpoint: stores Spotify credentials directly.
    Called from wundio.dev/docs/spotify-setup after user creates their app.
    """
    _write_env_key("SPOTIFY_CLIENT_ID", client_id)
    _write_env_key("SPOTIFY_CLIENT_SECRET", secret)
    
    # Clear cache so next request picks up new values
    from config import get_settings as _gs
    _gs.cache_clear()
    
    log_event("spotify", "Client-ID und Secret gespeichert via QR-Setup")
    logger.info("Spotify credentials saved via /api/spotify/setup")
    
    return HTMLResponse(_success_page(
        title="✓ Credentials gespeichert",
        message="Client-ID und Secret wurden erfolgreich auf der Box gespeichert.",
        instruction="Du kannst jetzt in den Einstellungen auf 'Mit Spotify verbinden' klicken.",
    ))


@router.get("/auth/start")
async def spotify_auth_start():
    """
    Redirect user to Spotify authorization page.
    Requires SPOTIFY_CLIENT_ID to be set (via /spotify/setup or manually).
    """
    from config import get_settings as _gs
    _gs.cache_clear()
    
    cfg = get_settings()
    if not cfg.spotify_client_id:
        return HTMLResponse(_error_page(
            title="Client ID fehlt",
            message="Bitte zuerst die Spotify App via QR-Code einrichten oder Client ID manuell in Einstellungen eintragen.",
        ), status_code=400)

    params = urllib.parse.urlencode({
        "client_id":     cfg.spotify_client_id,
        "response_type": "code",
        "redirect_uri":  _get_redirect_uri(),
        "scope":         SPOTIFY_SCOPES,
        "show_dialog":   "true",
    })
    auth_url = f"https://accounts.spotify.com/authorize?{params}"
    logger.info(f"Redirecting to Spotify auth: {auth_url}")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(code: str = "", error: str = ""):
    """
    Spotify redirects here after user authorization.
    Exchanges authorization code for access + refresh tokens.
    """
    if error:
        log_event("spotify", f"OAuth abgebrochen: {error}", level="WARN")
        return HTMLResponse(_error_page(
            title="Autorisierung abgebrochen",
            message=f"Fehler: {error}",
        ))

    if not code:
        return HTMLResponse(_error_page(
            title="Kein Autorisierungscode",
            message="Spotify hat keinen Code zurückgegeben.",
        ))

    cfg = get_settings()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        return HTMLResponse(_error_page(
            title="Fehlende Credentials",
            message="Client ID oder Secret fehlt in den Einstellungen.",
        ))

    # Exchange code for tokens
    try:
        creds = base64.b64encode(
            f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()
        ).decode()

        token_req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({
                "grant_type":   "authorization_code",
                "code":         code,
                "redirect_uri": _get_redirect_uri(),
            }).encode(),
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
        )

        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_data = json.loads(resp.read())

        refresh_token = token_data.get("refresh_token", "")

        if not refresh_token:
            return HTMLResponse(_error_page(
                title="Token-Fehler",
                message="Kein Refresh Token erhalten. Bitte erneut versuchen.",
            ))

        # Persist refresh token
        _write_env_key("SPOTIFY_REFRESH_TOKEN", refresh_token)

        # Invalidate cache
        from config import get_settings as _gs
        _gs.cache_clear()

        log_event("spotify", "Spotify erfolgreich autorisiert – Refresh Token gespeichert")
        logger.info("Spotify OAuth complete – refresh token stored")

        return HTMLResponse(_success_page(
            title="✓ Spotify verbunden",
            message="Dein Spotify-Account wurde erfolgreich mit Wundio verknüpft.",
            instruction="Refresh Token wurde gespeichert. Du kannst jetzt RFID-Tags Playlists zuweisen.",
        ))

    except Exception as e:
        logger.error(f"Spotify token exchange failed: {e}")
        log_event("spotify", f"OAuth Fehler: {e}", level="ERROR")
        return HTMLResponse(_error_page(
            title="Verbindung fehlgeschlagen",
            message=f"Fehler beim Token-Austausch: {e}",
        ))


def _success_page(title: str, message: str, instruction: str = "") -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Spotify – {title}</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
          font-family: -apple-system, sans-serif;
          background: #1A1814;
          color: #F5EFE3;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }}
        .card {{
          background: #2A2420;
          border: 1px solid #3D3630;
          border-radius: 1.5rem;
          padding: 2.5rem;
          max-width: 480px;
          width: 100%;
          text-align: center;
        }}
        .dot {{
          width: 3rem; height: 3rem;
          background: #22C55E;
          border-radius: 50%;
          margin: 0 auto 1.5rem;
        }}
        h1 {{ font-size: 1.4rem; color: #22C55E; margin-bottom: 0.75rem; }}
        p  {{ font-size: 0.95rem; color: #9E8E7A; line-height: 1.6; margin-bottom: 1.5rem; }}
        .note {{ font-size: 0.8rem; color: #6B5E50; margin-top: 1rem; }}
        a  {{
          display: inline-block;
          background: #F59C1A;
          color: #fff;
          text-decoration: none;
          padding: 0.7rem 1.8rem;
          border-radius: 0.75rem;
          font-weight: 600;
          font-size: 0.9rem;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="dot"></div>
        <h1>{title}</h1>
        <p>{message}</p>
        {f'<p class="note">{instruction}</p>' if instruction else ''}
        <a href="/settings">Zurück zu Einstellungen</a>
      </div>
    </body>
    </html>
    """


def _error_page(title: str, message: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Spotify – {title}</title>
      <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
          font-family: -apple-system, sans-serif;
          background: #1A1814;
          color: #F5EFE3;
          min-height: 100vh;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2rem;
        }}
        .card {{
          background: #2A2420;
          border: 1px solid #3D3630;
          border-radius: 1.5rem;
          padding: 2.5rem;
          max-width: 480px;
          width: 100%;
          text-align: center;
        }}
        .dot {{
          width: 3rem; height: 3rem;
          background: #FF6B6B;
          border-radius: 50%;
          margin: 0 auto 1.5rem;
        }}
        h1 {{ font-size: 1.4rem; color: #FF6B6B; margin-bottom: 0.75rem; }}
        p  {{ font-size: 0.95rem; color: #9E8E7A; line-height: 1.6; margin-bottom: 1.5rem; }}
        a  {{
          display: inline-block;
          background: #F59C1A;
          color: #fff;
          text-decoration: none;
          padding: 0.7rem 1.8rem;
          border-radius: 0.75rem;
          font-weight: 600;
          font-size: 0.9rem;
        }}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="dot"></div>
        <h1>{title}</h1>
        <p>{message}</p>
        <a href="/settings">Zurück zu Einstellungen</a>
      </div>
    </body>
    </html>
    """
