"""
Wundio – /api/playback routes
"""
from fastapi import APIRouter
from pydantic import BaseModel

from services.spotify import get_spotify_service
from services.buttons import get_button_service
from database import log_event

router = APIRouter(tags=["playback"])


class VolumeRequest(BaseModel):
    volume: int


@router.get("/state")
async def get_state():
    """Get current playback state."""
    spotify = get_spotify_service()
    return spotify.refresh_state().to_dict()


@router.post("/toggle")
async def toggle_playback():
    """Play/Pause toggle via button simulation."""
    buttons = get_button_service()
    await buttons.simulate_press("play_pause")
    log_event("playback", "Toggle Play/Pause via UI")
    return {"ok": True}


@router.post("/next")
async def next_track():
    """Skip to next track."""
    buttons = get_button_service()
    await buttons.simulate_press("next")
    log_event("playback", "Next track via UI")
    return {"ok": True}


@router.post("/prev")
async def previous_track():
    """Skip to previous track."""
    buttons = get_button_service()
    await buttons.simulate_press("prev")
    log_event("playback", "Previous track via UI")
    return {"ok": True}


@router.post("/volume")
async def set_volume(req: VolumeRequest):
    """Set playback volume (0-100)."""
    spotify = get_spotify_service()
    volume = max(0, min(100, req.volume))
    spotify.set_volume(volume)
    
    # Persist for current user
    from database import get_setting, get_engine, User
    from sqlmodel import Session
    
    active_user_id = get_setting("active_user_id")
    if active_user_id:
        try:
            user_id = int(active_user_id)
            with Session(get_engine()) as session:
                user = session.get(User, user_id)
                if user:
                    user.volume = volume
                    session.add(user)
                    session.commit()
        except ValueError:
            pass
    
    log_event("playback", f"Volume set to {volume}% via UI")
    return {"ok": True, "volume": volume}


@router.post("/play-uri")
async def play_uri(uri: str):
    """Start playback of a Spotify URI."""
    spotify = get_spotify_service()
    played = spotify.play_uri(uri)
    
    if played:
        log_event("playback", f"Playing URI via UI: {uri}")
        return {"ok": True, "uri": uri}
    else:
        log_event("playback", f"Failed to play URI: {uri} (API not configured)", level="WARN")
        return {"ok": False, "error": "Spotify Web API not configured"}