"""
Wundio – Spotify OAuth Flow (Decentralized)

Every user creates their own Spotify Developer App.
No central Wundio app → no single point of failure.

Flow:
  1. User visits Settings page
  2. Enters Client ID + Secret (saved to wundio.env via /api/settings/env/*)
  3. Clicks "Mit Spotify verbinden"
  4. /api/spotify/auth/start builds redirect URI from request host, stores it in
     OAuth state parameter (base64-encoded) to survive DHCP changes
  5. Spotify redirects to /api/spotify/callback?code=...&state=...
  6. Callback decodes redirect URI from state for token exchange
  7. Refresh token stored → redirect to /settings
"""
import base64
import json
import logging
import urllib.parse
import urllib.request

from fastapi import APIRouter, Query, Request
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


def _get_redirect_uri(request: Request) -> str:
    """
    Build callback URI from the incoming request's host.
    Using request.base_url ensures consistency regardless of whether
    the Pi is on wlan0/eth0 or what IP DHCP assigned.
    """
    base = str(request.base_url).rstrip("/")
    return f"{base}/api/spotify/callback"


def _encode_state(redirect_uri: str) -> str:
    """Encode redirect URI into OAuth state so callback uses same value."""
    payload = json.dumps({"redirect_uri": redirect_uri})
    return base64.urlsafe_b64encode(payload.encode()).decode()


def _decode_state(state: str) -> str | None:
    """Decode redirect URI from OAuth state. Returns None on failure."""
    try:
        payload = json.loads(base64.urlsafe_b64decode(state.encode()))
        return payload.get("redirect_uri")
    except Exception:
        return None


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
        if line.strip().startswith(f"{key}="):
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
    secret: str = Query(..., min_length=10),
):
    """
    QR-Scan endpoint: stores Spotify credentials directly.
    Called from wundio.dev/docs/spotify-setup after user creates their app.
    """
    _write_env_key("SPOTIFY_CLIENT_ID", client_id)
    _write_env_key("SPOTIFY_CLIENT_SECRET", secret)

    from config import get_settings as _gs
    _gs.cache_clear()

    log_event("spotify", "Client-ID und Secret gespeichert via QR-Setup")
    logger.info("Spotify credentials saved via /api/spotify/setup")

    return HTMLResponse(_success_page(
        title="✓ Credentials gespeichert",
        message="Client-ID und Secret wurden erfolgreich auf der Box gespeichert.",
        instruction="Du kannst jetzt in den Einstellungen auf 'Mit Spotify verbinden' klicken.",
        redirect_to="/settings",
    ))


@router.get("/auth/start")
async def spotify_auth_start(request: Request):
    """
    Redirect user to Spotify authorization page.
    Encodes the redirect URI into the OAuth state to ensure auth/start and
    callback always use the same URI, even if IP changes between requests.
    """
    from config import get_settings as _gs
    _gs.cache_clear()

    cfg = get_settings()
    if not cfg.spotify_client_id:
        return HTMLResponse(_error_page(
            title="Client ID fehlt",
            message="Bitte zuerst Client ID in den Einstellungen eintragen.",
            redirect_to="/settings",
        ), status_code=400)

    redirect_uri = _get_redirect_uri(request)
    state = _encode_state(redirect_uri)

    params = urllib.parse.urlencode({
        "client_id":     cfg.spotify_client_id,
        "response_type": "code",
        "redirect_uri":  redirect_uri,
        "scope":         SPOTIFY_SCOPES,
        "state":         state,
        "show_dialog":   "true",
    })
    auth_url = f"https://accounts.spotify.com/authorize?{params}"
    logger.info(f"Redirecting to Spotify auth, redirect_uri={redirect_uri}")
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def spotify_callback(
    code: str = "",
    error: str = "",
    state: str = "",
):
    """
    Spotify redirects here after user authorization.
    Decodes redirect URI from state parameter for token exchange.
    """
    if error:
        log_event("spotify", f"OAuth abgebrochen: {error}", level="WARN")
        return HTMLResponse(_error_page(
            title="Autorisierung abgebrochen",
            message=f"Fehler: {error}",
            redirect_to="/settings",
        ))

    if not code:
        return HTMLResponse(_error_page(
            title="Kein Autorisierungscode",
            message="Spotify hat keinen Code zurückgegeben.",
            redirect_to="/settings",
        ))

    # Decode redirect URI from state (must match what was sent to Spotify)
    redirect_uri = _decode_state(state) if state else None
    if not redirect_uri:
        # Fallback: reconstruct from env (legacy / direct URL access)
        cfg_fallback = get_settings()
        redirect_uri = f"http://localhost:{cfg_fallback.port}/api/spotify/callback"
        logger.warning(f"State missing or invalid – falling back to {redirect_uri}")

    cfg = get_settings()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        return HTMLResponse(_error_page(
            title="Fehlende Credentials",
            message="Client ID oder Secret fehlt in den Einstellungen.",
            redirect_to="/settings",
        ))

    try:
        creds = base64.b64encode(
            f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()
        ).decode()

        token_req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({
                "grant_type":   "authorization_code",
                "code":         code,
                "redirect_uri": redirect_uri,
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
                redirect_to="/settings",
            ))

        _write_env_key("SPOTIFY_REFRESH_TOKEN", refresh_token)

        from config import get_settings as _gs
        _gs.cache_clear()

        log_event("spotify", "Spotify erfolgreich autorisiert – Refresh Token gespeichert")
        logger.info("Spotify OAuth complete – refresh token stored")

        return HTMLResponse(_success_page(
            title="✓ Spotify verbunden",
            message="Dein Spotify-Account wurde erfolgreich mit Wundio verknüpft.",
            instruction="RFID-Tags können jetzt Playlists starten.",
            redirect_to="/settings",
        ))

    except Exception as e:
        logger.error(f"Spotify token exchange failed: {e}")
        log_event("spotify", f"OAuth Fehler: {e}", level="ERROR")
        return HTMLResponse(_error_page(
            title="Verbindung fehlgeschlagen",
            message=f"Fehler beim Token-Austausch: {e}",
            redirect_to="/settings",
        ))


# ── HTML response helpers ─────────────────────────────────────────────────────

def _success_page(title: str, message: str, instruction: str = "", redirect_to: str = "/settings") -> str:
    auto_redirect = f'<meta http-equiv="refresh" content="3;url={redirect_to}">'
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  {auto_redirect}
  <title>Spotify – {title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,sans-serif;background:#1A1814;color:#F5EFE3;
          min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}}
    .card{{background:#2A2420;border:1px solid #3D3630;border-radius:1.5rem;
           padding:2.5rem;max-width:480px;width:100%;text-align:center}}
    .dot{{width:3rem;height:3rem;background:#22C55E;border-radius:50%;margin:0 auto 1.5rem}}
    h1{{font-size:1.4rem;color:#22C55E;margin-bottom:.75rem}}
    p{{font-size:.95rem;color:#9E8E7A;line-height:1.6;margin-bottom:1rem}}
    .note{{font-size:.8rem;color:#6B5E50}}
    a{{display:inline-block;background:#F59C1A;color:#fff;text-decoration:none;
       padding:.7rem 1.8rem;border-radius:.75rem;font-weight:600;font-size:.9rem}}
  </style>
</head>
<body>
  <div class="card">
    <div class="dot"></div>
    <h1>{title}</h1>
    <p>{message}</p>
    {f'<p class="note">{instruction}</p>' if instruction else ''}
    <p class="note" style="margin-top:1.5rem">Weiterleitung in 3 Sekunden...</p>
    <a href="{redirect_to}" style="margin-top:1rem">Zurück zu Einstellungen</a>
  </div>
</body>
</html>"""


def _error_page(title: str, message: str, redirect_to: str = "/settings") -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Spotify – {title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{font-family:-apple-system,sans-serif;background:#1A1814;color:#F5EFE3;
          min-height:100vh;display:flex;align-items:center;justify-content:center;padding:2rem}}
    .card{{background:#2A2420;border:1px solid #3D3630;border-radius:1.5rem;
           padding:2.5rem;max-width:480px;width:100%;text-align:center}}
    .dot{{width:3rem;height:3rem;background:#EF4444;border-radius:50%;margin:0 auto 1.5rem}}
    h1{{font-size:1.4rem;color:#EF4444;margin-bottom:.75rem}}
    p{{font-size:.95rem;color:#9E8E7A;line-height:1.6;margin-bottom:1rem}}
    a{{display:inline-block;background:#F59C1A;color:#fff;text-decoration:none;
       padding:.7rem 1.8rem;border-radius:.75rem;font-weight:600;font-size:.9rem}}
  </style>
</head>
<body>
  <div class="card">
    <div class="dot"></div>
    <h1>{title}</h1>
    <p>{message}</p>
    <a href="{redirect_to}">Zurück zu Einstellungen</a>
  </div>
</body>
</html>"""