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
from services.buttons import build_default_service
from api.routes import system, users, rfid_routes, settings_routes, playback, wifi

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wundio")


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
    log_event("system", f"Wundio {cfg.app_version} starting on {hw.model}")

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

    # 6. Restore volume from last session
    saved_vol = get_setting("current_volume")
    if saved_vol and hw.feature_spotify:
        spotify.set_volume(int(saved_vol))

    # 7. Display state
    setup_complete = get_setting("setup_complete") == "true"
    if not setup_complete or get_setting("hotspot_active") == "true":
        display.show_setup(cfg.hotspot_ssid, cfg.hotspot_ip)
        log_event("system", "Setup mode active")
    else:
        display.show_idle()
        log_event("system", "Ready")

    logger.info(f"Wundio ready – http://{cfg.host}:{cfg.port}")
    logger.info(f"Hardware: {hw.model} | Features: {hw.to_dict()['features']}")

    yield

    # Shutdown
    buttons.stop()
    rfid.stop()
    spotify.stop()
    display.clear()
    log_event("system", "Wundio shutdown")


async def _on_rfid_scan(uid: str) -> None:
    from database import get_engine
    from models.user import resolve_rfid_action
    from sqlmodel import Session
    display = get_display()
    spotify = get_spotify_service()

    with Session(get_engine()) as session:
        action = resolve_rfid_action(session, uid)

    if action is None:
        display.show_error("Unbekannter Tag")
        log_event("rfid", f"Unknown tag: {uid}", level="WARN")
        return

    log_event("rfid", f"Tag: {uid} → {action}")

    if action["type"] == "user_login":
        from database import get_engine, User, set_setting
        from sqlmodel import Session
        with Session(get_engine()) as s:
            user = s.get(User, action["user_id"])
            if user:
                set_setting("active_user_id", str(user.id))
                spotify.set_volume(user.volume)
                display.show_user_login(user.display_name)

    elif action["type"] == "playlist":
        display.show_idle(f"▶ Playlist")
        # Spotify Web API play call will be added in Phase 2

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
    display = get_display()
    state   = spotify.get_state()

    log_event("buttons", f"Button: {name}")

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
