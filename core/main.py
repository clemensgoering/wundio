"""
Wundio – FastAPI Core Application

Entry point for the backend. Manages the application lifespan (startup/shutdown
of hardware services) and wires together the FastAPI routers.

Boot sequence:
  1. Display  – show boot screen immediately so the box looks alive
  2. Database – init SQLite, seed defaults, sync network state
  3. RFID     – attach scan callback, start polling loop
  4. Spotify  – spawn librespot subprocess
  5. Buttons  – register GPIO callbacks
  5b. Voice   – start wake-word + STT pipeline (Pi 4+ only, opt-in)
  6. Volume   – restore last saved level
  7. Display  – idle or setup screen depending on wifi state
"""

import logging
import asyncio
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings
from database import get_engine, init_db, get_setting, set_setting, log_event
from models.user import resolve_rfid_action
from services.hardware import get_profile
from services.display import get_display
from services.rfid import get_rfid_service
from services.spotify import get_spotify_service
from services.ai.voice import get_voice_orchestrator
from services.buttons import build_default_service
from api.routes.system_actions import router as system_actions_router
from api.routes import (
    system,
    users,
    rfid_routes,
    settings_routes,
    playback,
    wifi,
    voice,
    spotify_auth,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wundio")


# ── Network state sync ────────────────────────────────────────────────────────

def _sync_network_state() -> None:
    """Check actual network state on every boot and sync the DB flags.

    Fixes stale 'Setup ausstehend' / 'WLAN nicht konfiguriert' UI states when
    the Pi was flashed with WiFi credentials or is already connected to a network
    before the first Wundio startup.
    """
    import subprocess

    connected = False
    ssid = ""

    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=3,
        )
        connected = "inet " in result.stdout
    except Exception:
        pass

    if connected:
        try:
            r = subprocess.run(
                ["iwgetid", "wlan0", "--raw"],
                capture_output=True, text=True, timeout=3,
            )
            ssid = r.stdout.strip()
        except Exception:
            pass

    if connected:
        set_setting("wifi_configured", "true")
        set_setting("hotspot_active",  "false")
        if ssid:
            set_setting("wifi_ssid", ssid)
        set_setting("setup_complete", "true")
        logger.info(f"Network state synced: connected to '{ssid or 'unknown'}'")
    else:
        logger.info("Network state synced: no WiFi connection detected")


# ── RFID callback ─────────────────────────────────────────────────────────────

async def _on_rfid_scan(uid: str) -> None:
    """Handle a scanned RFID tag UID.

    Called by the RFID polling loop. Resolves the UID to an action (user login,
    playlist play, or hardware action) and dispatches accordingly.

    The last scanned UID and timestamp are always written to the DB so the web
    UI can show it in the tag-assignment modal (polling /api/rfid/last-scan).
    """
    from sqlmodel import Session

    display = get_display()
    spotify = get_spotify_service()

    set_setting("rfid_last_scan_uid", uid)
    set_setting("rfid_last_scan_ts",  str(int(time.time())))

    with Session(get_engine()) as session:
        action = resolve_rfid_action(session, uid)

    if action is None:
        display.show_error("Unbekannter Tag")
        log_event(
            "rfid",
            f"Unbekannte Karte/Figur aufgelegt (UID: {uid}) – noch nicht zugewiesen",
            level="WARN",
        )
        return

    if action["type"] == "user_login":
        from database import User
        from sqlmodel import Session as _Session
        with _Session(get_engine()) as s:
            user = s.get(User, action["user_id"])
            if user:
                set_setting("active_user_id", str(user.id))
                spotify.set_volume(user.volume)
                display.show_user_login(user.display_name)
                log_event("rfid", f"Kind eingeloggt: {user.display_name} (Lautstärke: {user.volume}%)")

    elif action["type"] == "playlist":
        uri       = action.get("spotify_uri", "")
        tag_label = action.get("label", "Playlist")
        if uri:
            # Always update the display immediately – play_uri may take up to 5 s
            display.show_idle(tag_label)
            played = await spotify.play_uri(uri)   # non-blocking via asyncio.to_thread
            if played:
                log_event("rfid", f"Playlist gestartet: {tag_label} ({uri})")
            else:
                log_event(
                    "rfid",
                    f"Playlist-Tag erkannt: {tag_label} – Spotify Web API nicht konfiguriert. "
                    "SPOTIFY_CLIENT_ID etc. in /etc/wundio/wundio.env eintragen.",
                    level="WARN",
                )
        else:
            log_event("rfid", f"Playlist-Tag {uid} hat keine URI – bitte im Dashboard ergänzen", level="WARN")

    elif action["type"] == "action":
        act = action["action"]
        if act == "stop":
            spotify.stop()
        elif act == "vol_up":
            spotify.set_volume(min(100, spotify.get_state().volume + 10))
        elif act == "vol_down":
            spotify.set_volume(max(0, spotify.get_state().volume - 10))


# ── Button callback ───────────────────────────────────────────────────────────

async def _on_button_press(name: str) -> None:
    """Handle a physical button press.

    Volume is controlled here by calling set_volume() directly.

    play_pause / next / prev are intentionally not handled in software:
    librespot registers as a Spotify Connect device and receives these commands
    natively via the Spotify protocol when the GPIO buttons trigger the matching
    media-key events. Adding a software layer here would duplicate that logic.

    If offline / non-Connect playback is needed in a future phase, keyboard
    event injection (e.g. via `evdev`) is the correct approach – all three
    buttons would call the same /api/playback/* endpoints the web UI uses.
    """
    spotify = get_spotify_service()
    log_event("buttons", f"Taste: {name.replace('_', ' ')} gedrückt")

    if name == "vol_up":
        spotify.set_volume(min(100, spotify.get_state().volume + 5))
    elif name == "vol_down":
        spotify.set_volume(max(0, spotify.get_state().volume - 5))


# ── Voice callback ────────────────────────────────────────────────────────────

async def _on_voice_action(intent) -> None:
    """Dispatch a parsed voice intent to the appropriate service.

    All voice commands ultimately call the same service methods as buttons and
    the web UI – there is no separate code path for voice.
    """
    spotify = get_spotify_service()
    state   = spotify.get_state()
    log_event("voice", f"Action: {intent.type} {intent.params}")

    if intent.type == "volume_up":
        spotify.set_volume(min(100, state.volume + intent.params.get("amount", 10)))
    elif intent.type == "volume_down":
        spotify.set_volume(max(0, state.volume - intent.params.get("amount", 10)))
    elif intent.type == "next":
        from services.buttons import get_button_service
        await get_button_service().simulate_press("next")
    elif intent.type == "prev":
        from services.buttons import get_button_service
        await get_button_service().simulate_press("prev")
    elif intent.type == "pause":
        from services.buttons import get_button_service
        await get_button_service().simulate_press("play_pause")
    elif intent.type == "user_switch":
        name = intent.params.get("name", "").strip()
        from database import User
        from sqlmodel import Session as _Session, select
        with _Session(get_engine()) as s:
            user = s.exec(
                select(User).where(User.display_name.ilike(f"%{name}%"))
            ).first()
            if user:
                spotify.set_volume(user.volume)
                get_display().show_user_login(user.display_name)


# ── App lifespan ──────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    hw  = get_profile()
    display = get_display()

    # 1. Display – show boot screen before anything else
    display.setup()
    display.show_boot(cfg.app_version)

    # 2. Database
    init_db(cfg.db_path)
    log_event("system", f"Wundio {cfg.app_version} gestartet auf {hw.model}")
    _sync_network_state()

    # 3. RFID
    rfid = get_rfid_service()
    if hw.feature_rfid:
        rfid.setup()
        rfid.on_scan(_on_rfid_scan)
        asyncio.create_task(rfid.run())

    # 4. Spotify (librespot)
    spotify = get_spotify_service()
    if hw.feature_spotify:
        spotify.setup()
        await spotify.start()

    # 5. Buttons
    buttons = build_default_service(cfg)
    from services import buttons as btn_module
    btn_module._service = buttons
    if hw.feature_buttons:
        buttons.on_press(_on_button_press)
        buttons.setup()
        asyncio.create_task(buttons.run())

    # 5b. Voice pipeline (Phase 3 – Pi 4+ only, user opt-in)
    voice = get_voice_orchestrator()
    voice_enabled = get_setting("voice_enabled") == "true"
    if voice_enabled and hw.pi_generation >= 4:
        voice.on_action(_on_voice_action)
        voice.setup(pi_generation=hw.pi_generation)
        asyncio.create_task(voice.run())
        log_event("voice", "Voice pipeline started")
    elif voice_enabled and hw.pi_generation < 4:
        log_event("voice", "Voice disabled: Pi 3 not supported for real-time STT")

    # 6. Restore volume from last session
    saved_vol = get_setting("current_volume")
    if saved_vol and hw.feature_spotify:
        spotify.set_volume(int(saved_vol))

    # 7. Display – idle or setup screen
    setup_complete = get_setting("setup_complete") == "true"
    if not setup_complete or get_setting("hotspot_active") == "true":
        display.show_setup(cfg.hotspot_ssid, cfg.hotspot_ip)
        log_event("system", "Ersteinrichtung aktiv – Warte auf WLAN-Verbindung")
    else:
        display.show_idle()
        log_event("system", "Bereit")

    logger.info(f"Wundio ready – http://{cfg.host}:{cfg.port}")
    logger.info(f"Hardware: {hw.model} | Features: {hw.to_dict()['features']}")

    yield

    # Shutdown – reverse order
    voice.stop()
    buttons.stop()
    rfid.stop()
    spotify.stop()
    display.clear()
    log_event("system", "Wundio beendet")


# ── FastAPI app ───────────────────────────────────────────────────────────────

cfg = get_settings()

app = FastAPI(
    title="Wundio",
    version=cfg.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# Two routers share the /api/system prefix intentionally:
#   system         → status, health, events, setup, restart
#   system_actions → whitelisted script execution with SSE output streaming
app.include_router(system.router,             prefix="/api/system")
app.include_router(users.router,              prefix="/api/users")
app.include_router(rfid_routes.router,        prefix="/api/rfid")
app.include_router(settings_routes.router,    prefix="/api/settings")
app.include_router(playback.router,           prefix="/api/playback")
app.include_router(wifi.router,               prefix="/api/wifi")
app.include_router(voice.router,              prefix="/api/voice")
app.include_router(spotify_auth.router,       prefix="/api/spotify")
app.include_router(system_actions_router,     prefix="/api/system")

_static = Path(cfg.static_dir)
if _static.exists():
    app.mount("/assets", StaticFiles(directory=str(_static / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(str(_static / "index.html"))
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Wundio API running. Web UI not built yet."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=cfg.host, port=cfg.port, reload=cfg.debug)