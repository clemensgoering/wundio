"""
Wundio – Spotify OAuth Flow
Implements Authorization Code Flow for local network devices.

Redirect URI: http://wundio.local:8000/api/spotify/callback
              (add this URL in your Spotify Developer App settings)

Flow:
  1. User enters Client ID + Secret in Settings
  2. User clicks "Mit Spotify verbinden"
  3. GET /api/spotify/auth/start  -> redirect to Spotify authorization page
  4. User authorizes in browser
  5. Spotify redirects to /api/spotify/callback?code=...
  6. FastAPI exchanges code for tokens
  7. Refresh token is stored in wundio.env
  8. User is redirected to /settings with success message
"""
import urllib.parse
import urllib.request
import base64
import json
import logging

from fastapi import APIRouter, Request
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


def _get_redirect_uri(request) -> str:
    """
    Build callback URI from the incoming request host.

    Spotify allows http:// only for localhost and IP addresses.
    Using the request host ensures the URI matches what the user registered
    in the Spotify Developer Dashboard.

    Register in Spotify Dashboard: http://<Pi-IP>:8000/api/spotify/callback
    Example: http://192.168.1.50:8000/api/spotify/callback
    """
    host = request.headers.get("host", f"localhost:{request.url.port or 8000}")
    return f"http://{host}/api/spotify/callback"


def _write_env_key(key: str, value: str) -> None:
    """Write a single key to wundio.env."""
    from pathlib import Path
    env_file = Path("/etc/wundio/wundio.env")
    if not env_file.exists():
        logger.warning("wundio.env not found – cannot persist token")
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


@router.get("/auth/start")
async def spotify_auth_start(request: Request):
    """
    Redirect user to Spotify authorization page.
    Requires SPOTIFY_CLIENT_ID to be set in wundio.env.
    """
    cfg = get_settings()
    if not cfg.spotify_client_id:
        return HTMLResponse("""
            <html><body style="font-family:sans-serif;padding:2rem;background:#1A1814;color:#fff">
            <h2 style="color:#F59C1A">Client ID fehlt</h2>
            <p>Bitte zuerst die <strong>Client ID</strong> in den Einstellungen eintragen.</p>
            <a href="/settings" style="color:#4ECDC4">Zurueck zu Einstellungen</a>
            </body></html>
        """, status_code=400)

    redirect_uri = _get_redirect_uri(request)
    params = urllib.parse.urlencode({
        "client_id":     cfg.spotify_client_id,
        "response_type": "code",
        "redirect_uri":  redirect_uri,
        "scope":         SPOTIFY_SCOPES,
        "show_dialog":   "true",
    })
    auth_url = f"https://accounts.spotify.com/authorize?{params}"
    logger.info(f"Redirecting to Spotify auth: {auth_url}")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(request: Request, code: str = "", error: str = ""):
    """
    Spotify redirects here after user authorization.
    Exchanges authorization code for access + refresh tokens.
    """
    if error:
        log_event("spotify", f"OAuth abgebrochen: {error}", level="WARN")
        return HTMLResponse(_result_page(
            success=False,
            message=f"Autorisierung abgebrochen: {error}"
        ))

    if not code:
        return HTMLResponse(_result_page(
            success=False,
            message="Kein Autorisierungscode erhalten."
        ))

    cfg = get_settings()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        return HTMLResponse(_result_page(
            success=False,
            message="Client ID oder Secret fehlt in den Einstellungen."
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
                "redirect_uri": _get_redirect_uri(request),
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
            return HTMLResponse(_result_page(
                success=False,
                message="Kein Refresh Token erhalten. Bitte erneut versuchen."
            ))

        # Persist refresh token in wundio.env
        _write_env_key("SPOTIFY_REFRESH_TOKEN", refresh_token)

        # Also invalidate settings cache so next request picks up new token
        from config import get_settings as _gs
        _gs.cache_clear()

        log_event("spotify", "Spotify erfolgreich autorisiert – Refresh Token gespeichert")
        logger.info("Spotify OAuth complete – refresh token stored")

        return HTMLResponse(_result_page(
            success=True,
            message="Spotify erfolgreich verbunden! Refresh Token wurde gespeichert."
        ))

    except Exception as e:
        logger.error(f"Spotify token exchange failed: {e}")
        log_event("spotify", f"OAuth Fehler: {e}", level="ERROR")
        return HTMLResponse(_result_page(
            success=False,
            message=f"Fehler beim Token-Austausch: {e}"
        ))


def _result_page(success: bool, message: str) -> str:
    color   = "#22C55E" if success else "#FF6B6B"
    heading = "Verbindung erfolgreich" if success else "Verbindung fehlgeschlagen"
    return f"""
    <!DOCTYPE html>
    <html lang="de">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>Spotify – {heading}</title>
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
          background: {color};
          border-radius: 50%;
          margin: 0 auto 1.5rem;
        }}
        h1 {{ font-size: 1.4rem; color: {color}; margin-bottom: 0.75rem; }}
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
        {"" if not success else ".note { font-size: 0.8rem; color: #6B5E50; margin-top: 1rem; }"}
      </style>
    </head>
    <body>
      <div class="card">
        <div class="dot"></div>
        <h1>{heading}</h1>
        <p>{message}</p>
        {"<p class='note'>Du kannst dieses Fenster schliessen oder zur App zurueckkehren.</p>" if success else ""}
        <a href="/settings">Zurueck zu Einstellungen</a>
      </div>
    </body>
    </html>
    """