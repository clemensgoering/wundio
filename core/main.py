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
from api.routes import system, users, rfid_routes, settings_routes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wundio")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown sequence."""
    cfg = get_settings()
    hw = get_profile()
    display = get_display()

    # 1. Display boot message immediately
    display.setup()
    display.show_boot(cfg.app_version)

    # 2. Init database
    init_db(cfg.db_path)
    log_event("system", f"Wundio {cfg.app_version} starting on {hw.model}")

    # 3. Init RFID if available on this hardware
    rfid = get_rfid_service()
    if hw.feature_rfid:
        rfid.setup()
        rfid.on_scan(_on_rfid_scan)
        asyncio.create_task(rfid.run())

    # 4. Show appropriate screen
    setup_complete = get_setting("setup_complete") == "true"
    hotspot_active = get_setting("hotspot_active") == "true"

    if not setup_complete or hotspot_active:
        display.show_setup(cfg.hotspot_ssid, cfg.hotspot_ip)
        log_event("system", "Setup mode active")
    else:
        display.show_idle()
        log_event("system", "Ready")

    logger.info(f"Wundio ready – http://{cfg.host}:{cfg.port}")
    logger.info(f"Hardware: {hw.model} | Features: {hw.to_dict()['features']}")

    yield

    # Shutdown
    rfid.stop()
    display.clear()
    log_event("system", "Wundio shutdown")


async def _on_rfid_scan(uid: str) -> None:
    """Central RFID dispatch – called by RfidService on every scan."""
    from database import get_engine, log_event
    from models.user import resolve_rfid_action
    from sqlmodel import Session

    with Session(get_engine()) as session:
        action = resolve_rfid_action(session, uid)

    if action is None:
        logger.info(f"Unknown RFID tag: {uid}")
        get_display().show_error("Unbekannter Tag")
        log_event("rfid", f"Unknown tag: {uid}", level="WARN")
        return

    log_event("rfid", f"Tag scanned: {uid} → {action}")
    logger.info(f"RFID action: {action}")
    # Action dispatch will be extended in Phase 1 (Spotify, user login, etc.)


# ── App ───────────────────────────────────────────────────────────────────────

cfg = get_settings()

app = FastAPI(
    title="Wundio",
    version=cfg.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url=None,
)

# API routes
app.include_router(system.router,          prefix="/api/system")
app.include_router(users.router,           prefix="/api/users")
app.include_router(rfid_routes.router,     prefix="/api/rfid")
app.include_router(settings_routes.router, prefix="/api/settings")

# Serve React SPA from /web/dist
_static = Path(cfg.static_dir)
if _static.exists():
    app.mount("/assets", StaticFiles(directory=str(_static / "assets")), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        index = _static / "index.html"
        return FileResponse(str(index))
else:
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Wundio API running. Web UI not built yet."}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=cfg.host, port=cfg.port, reload=cfg.debug)
