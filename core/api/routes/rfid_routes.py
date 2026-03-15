"""
Wundio – /api/rfid routes
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from database import get_engine, log_event, RfidTag

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


@router.post("/assign", response_model=RfidTag)
async def assign_tag(data: TagAssign):
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


@router.post("/mock-scan/{uid}")
async def mock_scan(uid: str):
    """Trigger a simulated RFID scan (dev/testing only)."""
    from services.rfid import get_rfid_service
    await get_rfid_service().write_uid_mock(uid)
    return {"scanned": uid}
