"""
Wundio – /api/playback routes
Controls librespot / reports current state.
"""
import asyncio

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.spotify import get_spotify_service
from services.buttons import get_button_service
from services.feedback import feedback
from database import log_event, set_setting

router = APIRouter(tags=["playback"])


class VolumeRequest(BaseModel):
    volume: int   # 0-100


class ActiveUserRequest(BaseModel):
    user_id: int


@router.get("/state")
async def get_state():
    """Current playback state (track, artist, playing, volume)."""
    svc = get_spotify_service()
    return svc.refresh_state().to_dict()


@router.post("/toggle")
async def toggle_play_pause():
    """Toggle play/pause on the active Spotify device."""
    svc = get_spotify_service()
    svc.refresh_state()
    is_playing = svc.get_state().playing
    ok = await asyncio.to_thread(svc.toggle_play_pause)
    if ok:
        new_state = "Pause" if is_playing else "Abspielen"
        color     = "white"  if is_playing else "teal"
        event     = "playback_pause" if is_playing else "playback_start"
        await feedback(event, new_state, color=color, duration_ms=800)
        log_event("playback", f"Toggle: {new_state}")
    return {"ok": ok, "playing": not is_playing}


@router.post("/next")
async def next_track():
    """Skip to the next track."""
    svc = get_spotify_service()
    ok = await asyncio.to_thread(svc.next_track)
    if ok:
        await feedback("track_next", "Nächster Titel", color="teal", duration_ms=600)
        log_event("playback", "Nächster Titel")
    return {"ok": ok}


@router.post("/prev")
async def prev_track():
    """Skip to the previous track."""
    svc = get_spotify_service()
    ok = await asyncio.to_thread(svc.prev_track)
    if ok:
        await feedback("track_prev", "Vorheriger Titel", color="teal", duration_ms=600)
        log_event("playback", "Vorheriger Titel")
    return {"ok": ok}


@router.post("/volume")
async def set_volume(req: VolumeRequest):
    if not 0 <= req.volume <= 100:
        raise HTTPException(status_code=422, detail="Volume must be 0-100")
    svc = get_spotify_service()
    svc.set_volume(req.volume)
    set_setting("current_volume", str(req.volume))
    await feedback("volume_change", f"Lautstärke {req.volume}%", color="blue", duration_ms=600)
    log_event("playback", f"Volume set to {req.volume}")
    return {"volume": req.volume}


@router.post("/active-user")
async def set_active_user(req: ActiveUserRequest):
    """Switch active user profile (called after RFID user-login)."""
    from database import get_engine, User
    from sqlmodel import Session
    with Session(get_engine()) as s:
        user = s.get(User, req.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        name = user.display_name
        vol  = user.volume
    set_setting("active_user_id", str(req.user_id))
    get_spotify_service().set_volume(vol)
    from services.display import get_display
    get_display().show_user_login(name)
    log_event("playback", f"Active user: {name} (vol={vol})")
    return {"active_user": name, "volume": vol}


@router.post("/button/{name}")
async def simulate_button(name: str):
    """Simulate a physical button press – dev/testing only."""
    valid = {"play_pause", "next", "prev", "vol_up", "vol_down"}
    if name not in valid:
        raise HTTPException(status_code=422, detail=f"Unknown button. Valid: {valid}")
    await get_button_service().simulate_press(name)
    return {"pressed": name}