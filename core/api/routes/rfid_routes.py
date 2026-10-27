"""
Wundio – /api/rfid routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_engine, log_event, RfidTag
from services import card_learning

router = APIRouter(tags=["rfid"])


class TagAssign(BaseModel):
    uid: str
    label: str
    tag_type: str = "user"          # "user" | "playlist" | "action"
    user_id: Optional[int] = None
    spotify_uri: Optional[str] = None
    action: Optional[str] = None


@router.get("/", response_model=List[RfidTag])
async def list_tags():
    with Session(get_engine()) as session:
        return session.exec(select(RfidTag)).all()


class LearnRequest(BaseModel):
    seconds: int = card_learning.DEFAULT_LEARN_S


@router.post("/assign", response_model=RfidTag)
async def assign_tag(data: TagAssign):
    if data.tag_type == "playlist":
        uri = card_learning.normalize_spotify_uri(data.spotify_uri or "")
        if not uri:
            raise HTTPException(
                status_code=422,
                detail="Ungültiger Spotify-Link – erwartet open.spotify.com/... oder spotify:album:...",
            )
        data.spotify_uri = uri
    with Session(get_engine()) as session:
        existing = session.exec(
            select(RfidTag).where(RfidTag.uid == data.uid)
        ).first()
        if existing:
            # Re-assign
            for field, value in data.model_dump().items():
                setattr(existing, field, value)
            session.add(existing)
            session.commit()
            session.refresh(existing)
            log_event("rfid", f"Tag re-assigned: {data.uid} → {data.tag_type}")
            return existing
        tag = RfidTag(**data.model_dump())
        session.add(tag)
        session.commit()
        session.refresh(tag)
        log_event("rfid", f"Tag assigned: {data.uid} → {data.tag_type}")
        return tag


@router.post("/mock-scan/{uid}")
async def mock_scan(uid: str):
    """Trigger a simulated RFID scan (dev/testing only)."""
    from services.rfid import get_rfid_service
    await get_rfid_service().write_uid_mock(uid)
    return {"scanned": uid}


@router.get("/last-scan")
async def last_scan():
    """Return the most recently scanned UID and its timestamp.

    The UI polls this endpoint while the 'assign tag' modal is open.
    Returns uid='' if no scan has occurred yet or scan is older than 30s.
    """
    from database import get_setting
    import time
    uid = get_setting("rfid_last_scan_uid", "")
    ts_str = get_setting("rfid_last_scan_ts", "0")
    try:
        ts = int(ts_str)
    except ValueError:
        ts = 0
    # Only return scans from the last 30 seconds
    age = int(time.time()) - ts
    if age > 30:
        uid = ""
    return {"uid": uid, "age_seconds": age}


# ── Card learning ("play it, then hold the card to the box") ─────────────────

def _learn_status() -> dict:
    from services.spotify import get_spotify_service
    state = get_spotify_service().refresh_state()
    target = card_learning.learnable_from_state(state) if state.playing else None
    return {
        "armed":        card_learning.is_armed(),
        "seconds_left": card_learning.seconds_left(),
        "auto_learn":   card_learning.auto_learn_enabled(),
        "now_playing":  target,
    }


@router.get("/learn")
async def learn_status():
    """Learn mode state + what a card would be bound to right now."""
    import asyncio
    return await asyncio.to_thread(_learn_status)


@router.post("/learn")
async def learn_start(req: LearnRequest):
    """Bind the next scanned card (new or existing) to the current playback."""
    card_learning.arm(req.seconds)
    log_event("rfid", "Anlern-Modus aktiv – nächste Karte übernimmt die aktuelle Wiedergabe")
    return {"armed": True, "seconds_left": card_learning.seconds_left()}


@router.delete("/learn")
async def learn_cancel():
    card_learning.disarm()
    return {"armed": False, "seconds_left": 0}


# Catch-all path parameter – keep last so fixed paths like /learn win
@router.delete("/{tag_uid}")
async def delete_tag(tag_uid: str):
    with Session(get_engine()) as session:
        tag = session.exec(
            select(RfidTag).where(RfidTag.uid == tag_uid)
        ).first()
        if not tag:
            raise HTTPException(status_code=404, detail="Tag not found")
        session.delete(tag)
        session.commit()
        return {"ok": True}
