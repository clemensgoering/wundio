"""
Wundio – RFID action resolver
"""
from typing import Optional
from sqlmodel import Session, select
from database import RfidTag


def resolve_rfid_action(session: Session, uid: str) -> Optional[dict]:
    """
    Look up a tag UID and return a structured action dict, or None if unknown.

    Returns:
        {"type": "user_login", "user_id": 1} |
        {"type": "playlist",   "spotify_uri": "spotify:playlist:..."} |
        {"type": "action",     "action": "stop"} |
        None
    """
    tag = session.exec(select(RfidTag).where(RfidTag.uid == uid)).first()
    if tag is None:
        return None

    if tag.tag_type == "user" and tag.user_id:
        return {"type": "user_login", "user_id": tag.user_id}
    if tag.tag_type == "playlist" and tag.spotify_uri:
        return {"type": "playlist", "spotify_uri": tag.spotify_uri}
    if tag.tag_type == "action" and tag.action:
        return {"type": "action", "action": tag.action}

    return None
