"""
Wundio – Spotify OAuth Flow via wundio.dev relay

Flow:
  1. auth/start → Spotify mit redirect_uri=https://wundio.dev/spotify-callback
     state = base64(json({pi_origin: "http://192.168.x.x:8000"}))
  2. Spotify → https://wundio.dev/spotify-callback?code=...&state=...
  3. wundio.dev/spotify-callback (Next.js) dekodiert pi_origin aus state,
     leitet weiter: http://{pi}:8000/api/spotify/callback?code=...&state=...
  4. Pi-Backend tauscht code gegen token – mit redirect_uri=https://wundio.dev/spotify-callback
     (muss exakt dem Wert entsprechen der bei Spotify eingetragen ist)
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

RELAY_REDIRECT_URI = "https://wundio.dev/spotify-callback"

SPOTIFY_SCOPES = " ".join([
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "playlist-read-private",
    "playlist-read-collaborative",
])

ENV_FILE = Path("/etc/wundio/wundio.env")


def _read_env_key(key: str) -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return ""


def _detect_local_ip() -> str:
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


def _get_pi_origin() -> str:
    """
    Returns http://{pi-ip}:8000 – the local address the relay will forward to.
    Reads PI_LOCAL_IP from wundio.env first (set by UI), falls back to detection.
    """
    stored_ip = _read_env_key("PI_LOCAL_IP").strip()
    ip = stored_ip if stored_ip else _detect_local_ip()
    cfg = get_settings()
    return f"http://{ip}:{cfg.port}"


def _encode_state(pi_origin: str) -> str:
    """
    Encode pi_origin into state.
    Format is compatible with the existing wundio.dev/spotify-callback relay page
    which does: atob(state) → pi_origin.
    """
    return base64.urlsafe_b64encode(pi_origin.encode()).decode()


def _decode_state(state: str) -> str | None:
    """Decode pi_origin from state parameter."""
    try:
        decoded = base64.urlsafe_b64decode(
            state.replace("-", "+").replace("_", "/") + "=="
        ).decode()
        # Must look like an http origin
        if decoded.startswith("http"):
            return decoded
        return None
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
    Redirect to Spotify. Uses https://wundio.dev/spotify-callback as redirect_uri
    (HTTPS, accepted by Spotify). Pi origin is encoded in state for the relay.
    """
    from config import get_settings as _gs
    _gs.cache_clear()

    cfg = get_settings()
    if not cfg.spotify_client_id:
        return HTMLResponse(_error_page(
            title="Client ID fehlt",
            message="Bitte zuerst Client ID in den Einstellungen eintragen.",
        ), status_code=400)

    pi_origin = _get_pi_origin()
    state = _encode_state(pi_origin)
    logger.info("Spotify auth/start – pi_origin=%s relay=%s", pi_origin, RELAY_REDIRECT_URI)

    params = urllib.parse.urlencode({
        "client_id":     cfg.spotify_client_id,
        "response_type": "code",
        "redirect_uri":  RELAY_REDIRECT_URI,
        "scope":         SPOTIFY_SCOPES,
        "state":         state,
        "show_dialog":   "true",
    })
    return RedirectResponse(url=f"https://accounts.spotify.com/authorize?{params}")


@router.get("/callback")
async def spotify_callback(code: str = "", error: str = "", state: str = ""):
    """
    Called by the wundio.dev relay after Spotify authorizes.
    Token exchange uses RELAY_REDIRECT_URI (must match Spotify app config).
    """
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

    cfg = get_settings()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        return HTMLResponse(_error_page(
            title="Fehlende Credentials",
            message="Client ID oder Secret fehlt.",
        ))

    try:
        creds = base64.b64encode(
            f"{cfg.spotify_client_id}:{cfg.spotify_client_secret}".encode()
        ).decode()

        # redirect_uri MUST be the relay URI – same value sent to Spotify in auth/start
        token_req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({
                "grant_type":   "authorization_code",
                "code":         code,
                "redirect_uri": RELAY_REDIRECT_URI,
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