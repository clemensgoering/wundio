"""
Wundio – Spotify OAuth Flow (Decentralized)

Redirect URI resolution (priority order):
  1. SPOTIFY_REDIRECT_URI in wundio.env  ← set by InteractiveSpotifySetup Step 1
  2. Auto-detected IP (wlan0 → eth0 → 127.0.0.1)

The URI is embedded in the OAuth state so auth/start and callback
always use the same value regardless of how the Pi is accessed.
"""
import base64
import json
import logging
import urllib.parse
import urllib.request
from pathlib import Path

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

ENV_FILE = Path("/etc/wundio/wundio.env")


def _read_env_key(key: str) -> str:
    """Read a single key directly from wundio.env (bypasses pydantic cache)."""
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def _detect_local_ip() -> str:
    """Try wlan0, then eth0, then localhost."""
    import subprocess
    for iface in ("wlan0", "eth0"):
        try:
            out = subprocess.run(
                ["ip", "-4", "addr", "show", iface],
                capture_output=True, text=True, timeout=2,
            ).stdout
            for line in out.splitlines():
                if "inet " in line:
                    return line.split()[1].split("/")[0]
        except Exception:
            pass
    return "127.0.0.1"


def _get_redirect_uri() -> str:
    """
    Returns the canonical redirect URI.
    Reads directly from wundio.env so it always reflects what the user
    entered in the Spotify Developer App – independent of pydantic cache
    or how the browser accesses the Pi (IP vs wundio.local).
    """
    stored = _read_env_key("SPOTIFY_REDIRECT_URI").strip()
    if stored:
        logger.debug("Using stored redirect URI: %s", stored)
        return stored
    cfg = get_settings()
    ip = _detect_local_ip()
    fallback = f"http://{ip}:{cfg.port}/api/spotify/callback"
    logger.warning("SPOTIFY_REDIRECT_URI not set – falling back to %s", fallback)
    return fallback


def _encode_state(redirect_uri: str) -> str:
    return base64.urlsafe_b64encode(
        json.dumps({"redirect_uri": redirect_uri}).encode()
    ).decode()


def _decode_state(state: str) -> str | None:
    try:
        data = json.loads(base64.urlsafe_b64decode(state.encode()))
        uri = data.get("redirect_uri")
        return uri if isinstance(uri, str) and uri else None
    except Exception:
        return None


def _write_env_key(key: str, value: str) -> None:
    if not ENV_FILE.exists():
        logger.warning("wundio.env not found – cannot persist %s", key)
        return
    lines = ENV_FILE.read_text().splitlines()
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
    ENV_FILE.write_text("\n".join(new_lines) + "\n")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/setup")
async def spotify_setup(
    client_id: str = Query(..., min_length=10),
    secret: str = Query(..., min_length=10),
):
    """QR-Scan endpoint: stores Spotify credentials directly."""
    _write_env_key("SPOTIFY_CLIENT_ID", client_id)
    _write_env_key("SPOTIFY_CLIENT_SECRET", secret)
    from config import get_settings as _gs
    _gs.cache_clear()
    log_event("spotify", "Client-ID und Secret gespeichert via QR-Setup")
    return HTMLResponse(_success_page(
        title="Credentials gespeichert",
        message="Client-ID und Secret wurden gespeichert.",
        instruction="Du kannst jetzt in den Einstellungen auf 'Mit Spotify verbinden' klicken.",
    ))


@router.get("/auth/start")
async def spotify_auth_start():
    """
    Redirect to Spotify authorization page.
    Uses SPOTIFY_REDIRECT_URI from wundio.env – set by the UI setup guide
    when the user confirms their IP in Step 1.
    """
    from config import get_settings as _gs
    _gs.cache_clear()

    cfg = get_settings()
    if not cfg.spotify_client_id:
        return HTMLResponse(_error_page(
            title="Client ID fehlt",
            message="Bitte zuerst Client ID in den Einstellungen eintragen.",
        ), status_code=400)

    redirect_uri = _get_redirect_uri()
    state = _encode_state(redirect_uri)
    logger.info("Spotify auth/start – redirect_uri=%s", redirect_uri)

    params = urllib.parse.urlencode({
        "client_id":     cfg.spotify_client_id,
        "response_type": "code",
        "redirect_uri":  redirect_uri,
        "scope":         SPOTIFY_SCOPES,
        "state":         state,
        "show_dialog":   "true",
    })
    return RedirectResponse(url=f"https://accounts.spotify.com/authorize?{params}")


@router.get("/callback")
async def spotify_callback(code: str = "", error: str = "", state: str = ""):
    """Exchange authorization code for tokens."""
    if error:
        log_event("spotify", f"OAuth abgebrochen: {error}", level="WARN")
        return HTMLResponse(_error_page(
            title="Autorisierung abgebrochen",
            message=f"Fehler von Spotify: {error}",
        ))

    if not code:
        return HTMLResponse(_error_page(
            title="Kein Autorisierungscode",
            message="Spotify hat keinen Code zurückgegeben.",
        ))

    # Decode URI from state – must match exactly what was sent to Spotify
    redirect_uri = _decode_state(state) if state else None
    if not redirect_uri:
        redirect_uri = _get_redirect_uri()
        logger.warning("State missing/invalid – using env URI: %s", redirect_uri)

    cfg = get_settings()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        return HTMLResponse(_error_page(
            title="Fehlende Credentials",
            message="Client ID oder Secret fehlt. Bitte Einstellungen prüfen.",
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
            ))

        _write_env_key("SPOTIFY_REFRESH_TOKEN", refresh_token)
        from config import get_settings as _gs
        _gs.cache_clear()

        log_event("spotify", "Spotify erfolgreich autorisiert – Refresh Token gespeichert")
        return HTMLResponse(_success_page(
            title="Spotify verbunden",
            message="Dein Spotify-Account wurde erfolgreich verknüpft.",
            instruction="RFID-Tags können jetzt Playlists starten.",
        ))

    except Exception as exc:
        logger.error("Spotify token exchange failed: %s", exc)
        log_event("spotify", f"OAuth Fehler: {exc}", level="ERROR")
        return HTMLResponse(_error_page(
            title="Verbindung fehlgeschlagen",
            message=f"Fehler beim Token-Austausch: {exc}",
        ))


# ── HTML helpers ──────────────────────────────────────────────────────────────

def _success_page(title: str, message: str, instruction: str = "") -> str:
    instr_html = f'<p class="note">{instruction}</p>' if instruction else ""
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <meta http-equiv="refresh" content="3;url=/settings">
  <title>Spotify - {title}</title>
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
    <h1>&#x2713; {title}</h1>
    <p>{message}</p>
    {instr_html}
    <p class="note" style="margin-top:1.5rem">Weiterleitung in 3 Sekunden...</p>
    <a href="/settings" style="margin-top:1rem">Einstellungen</a>
  </div>
</body>
</html>"""


def _error_page(title: str, message: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
  <meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>Spotify - {title}</title>
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
    <a href="/settings">Einstellungen</a>
  </div>
</body>
</html>"""