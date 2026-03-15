"""
Wundio – FastAPI Core Application
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from config import get_settings
from database import init_db, get_setting, set_setting, log_event
from services.hardware import get_profile
from services.display import get_display
from services.rfid import get_rfid_service
from services.spotify import get_spotify_service
from services.ai.voice import get_voice_orchestrator
from services.buttons import build_default_service
from api.routes import system, users, rfid_routes, settings_routes, playback, wifi, voice

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wundio")


def _sync_network_state() -> None:
    """
    On every boot: check actual network state and sync DB flags.
    Fixes 'Setup ausstehend' and 'WLAN nicht konfiguriert' when the Pi
    was flashed with WiFi credentials or is already connected.
    """
    import subprocess

    # Check if wlan0 has an IP address (= connected to a network)
    connected = False
    ssid = ""
    try:
        result = subprocess.run(
            ["ip", "-4", "addr", "show", "wlan0"],
            capture_output=True, text=True, timeout=3
        )
        connected = "inet " in result.stdout
    except Exception:
        pass

    # Try to get SSID if connected
    if connected:
        try:
            r = subprocess.run(
                ["iwgetid", "wlan0", "--raw"],
                capture_output=True, text=True, timeout=3
            )
            ssid = r.stdout.strip()
        except Exception:
            pass

    if connected:
        set_setting("wifi_configured", "true")
        set_setting("hotspot_active",  "false")
        if ssid:
            set_setting("wifi_ssid", ssid)
        # Mark setup complete when connected – user can reach the dashboard
        set_setting("setup_complete", "true")
        logger.info(f"Network state synced: connected to '{ssid or 'unknown'}'")
    else:
        # Not connected – hotspot mode or first run
        logger.info("Network state synced: no WiFi connection detected")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    hw  = get_profile()
    display = get_display()

    # 1. Display boot immediately
    display.setup()
    display.show_boot(cfg.app_version)

    # 2. Database
    init_db(cfg.db_path)
    log_event("system", f"Wundio {cfg.app_version} gestartet auf {hw.model}")

    # 2b. Auto-detect WiFi and setup state on every boot
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

    # 5b. Voice pipeline (Phase 3 – hardware-gated)
    voice = get_voice_orchestrator()
    voice_enabled = get_setting("voice_enabled") == "true"
    if voice_enabled and hw.pi_generation >= 4:
        voice.on_action(_on_voice_action)
        voice.setup(pi_generation=hw.pi_generation)
        asyncio.create_task(voice.run())
        log_event("voice", "Voice pipeline started")
    elif hw.pi_generation < 4:
        log_event("voice", "Voice disabled: Pi 3 not supported for real-time STT")

    # 6. Restore volume from last session
    saved_vol = get_setting("current_volume")
    if saved_vol and hw.feature_spotify:
        spotify.set_volume(int(saved_vol))

    # 7. Display state
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

    # Shutdown
    voice.stop()
    buttons.stop()
    rfid.stop()
    spotify.stop()
    display.clear()
    log_event("system", "Wundio beendet")


async def _on_rfid_scan(uid: str) -> None:
    from database import get_engine
    from models.user import resolve_rfid_action
    from sqlmodel import Session
    display = get_display()
    spotify = get_spotify_service()

    import time as _time
    # Always store last scanned UID so the UI can pick it up for tag assignment
    set_setting("rfid_last_scan_uid", uid)
    set_setting("rfid_last_scan_ts",  str(int(_time.time())))

    with Session(get_engine()) as session:
        action = resolve_rfid_action(session, uid)

    if action is None:
        display.show_error("Unbekannter Tag")
        log_event("rfid", f"Unbekannte Karte/Figur aufgelegt (UID: {uid}) – noch nicht zugewiesen", level="WARN")
        return

    # Human-readable log is written per action type below

    if action["type"] == "user_login":
        from database import get_engine, User
        from sqlmodel import Session as _Session
        with _Session(get_engine()) as s:
            user = s.get(User, action["user_id"])
            if user:
                set_setting("active_user_id", str(user.id))
                spotify.set_volume(user.volume)
                display.show_user_login(user.display_name)
                log_event("rfid", f"Kind eingeloggt: {user.display_name} (Lautstärke: {user.volume}%)")

    elif action["type"] == "playlist":
        uri = action.get("spotify_uri", "")
        tag_label = action.get("label", "Playlist")
        if uri:
            played = spotify.play_uri(uri)
            if played:
                display.show_idle(tag_label)
                log_event("rfid", f"Playlist gestartet: {tag_label} ({uri})")
            else:
                display.show_idle(tag_label)
                log_event(
                    "rfid",
                    f"Playlist-Tag erkannt: {tag_label} – Spotify Web API nicht konfiguriert. "
                    "SPOTIFY_CLIENT_ID etc. in /etc/wundio/wundio.env eintragen.",
                    level="WARN"
                )
        else:
            log_event("rfid", f"Playlist-Tag {uid} hat keine URI – bitte im Dashboard ergänzen", level="WARN")

    elif action["type"] == "action":
        act = action["action"]
        if act == "stop":
            spotify.stop()
        elif act == "vol_up":
            new_vol = min(100, spotify.get_state().volume + 10)
            spotify.set_volume(new_vol)
        elif act == "vol_down":
            new_vol = max(0, spotify.get_state().volume - 10)
            spotify.set_volume(new_vol)


async def _on_button_press(name: str) -> None:
    spotify = get_spotify_service()
    state   = spotify.get_state()

    log_event("buttons", f"Taste: {name.replace('_', ' ')} gedrückt")

    if name == "vol_up":
        spotify.set_volume(min(100, state.volume + 5))
    elif name == "vol_down":
        spotify.set_volume(max(0, state.volume - 5))
    # play_pause / next / prev: librespot handles these via Spotify Connect
    # We'll add keyboard-event injection in Phase 2 if needed


# ── App ───────────────────────────────────────────────────────────────────────

cfg = get_settings()

app = FastAPI(
    title="Wundio",
    version=cfg.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

app.include_router(system.router,          prefix="/api/system")
app.include_router(users.router,           prefix="/api/users")
app.include_router(rfid_routes.router,     prefix="/api/rfid")
app.include_router(settings_routes.router, prefix="/api/settings")
app.include_router(playback.router,        prefix="/api/playback")
app.include_router(wifi.router,             prefix="/api/wifi")
app.include_router(voice.router,             prefix="/api/voice")

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


async def _on_voice_action(intent) -> None:
    """Dispatch voice intents to hardware services."""
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
        from database import get_engine, User
        from sqlmodel import Session as _Session, select
        with _Session(get_engine()) as s:
            user = s.exec(
                select(User).where(User.display_name.ilike(f"%{name}%"))
            ).first()
            if user:
                spotify.set_volume(user.volume)
                from services.display import get_display
                get_display().show_user_login(user.display_name)