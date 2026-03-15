"""
Wundio – Database Setup (SQLite via aiosqlite + SQLModel)
Schema for Phase 0: Users, RFID Tags, Settings, System Log
"""

import logging
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

from sqlmodel import SQLModel, Field, create_engine, Session, select
from sqlalchemy import event

logger = logging.getLogger(__name__)


# ── Models ────────────────────────────────────────────────────────────────────

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    display_name: str
    avatar_emoji: str = Field(default="🎵")  # simple avatar for OLED
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=_now)

    # Spotify
    spotify_playlist_id: Optional[str] = None
    spotify_playlist_name: Optional[str] = None
    volume: int = Field(default=70, ge=0, le=100)


class RfidTag(SQLModel, table=True):
    __tablename__ = "rfid_tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    uid: str = Field(unique=True, index=True)    # hex string from RC522
    label: str = Field(default="")
    tag_type: str = Field(default="user")        # "user" | "playlist" | "action"
    # For type="user": ref to users.id
    user_id: Optional[int] = Field(default=None, foreign_key="users.id")
    # For type="playlist": Spotify playlist URI
    spotify_uri: Optional[str] = None
    # For type="action": e.g. "vol_up", "stop", "sleep_timer"
    action: Optional[str] = None
    created_at: datetime = Field(default_factory=_now)


class SystemSetting(SQLModel, table=True):
    __tablename__ = "system_settings"

    key: str = Field(primary_key=True)
    value: str
    updated_at: datetime = Field(default_factory=_now)


class SystemEvent(SQLModel, table=True):
    """Lightweight event log – ring buffer pattern (keep last 500)."""
    __tablename__ = "system_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    level: str = Field(default="INFO")          # INFO | WARN | ERROR
    source: str = Field(default="system")       # rfid | spotify | buttons | ai ...
    message: str
    created_at: datetime = Field(default_factory=_now)


# ── Engine ────────────────────────────────────────────────────────────────────

_engine = None


def get_engine():
    global _engine
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _engine


def init_db(db_path: str = "/var/lib/wundio/wundio.db") -> None:
    global _engine

    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    _engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    # Enable WAL mode for better concurrent read/write on Pi SD cards
    @event.listens_for(_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SQLModel.metadata.create_all(_engine)
    _seed_defaults()
    logger.info(f"Database initialized at {db_path}")


def _seed_defaults() -> None:
    """Insert default system settings if not present."""
    defaults = {
        "setup_complete": "false",
        "wifi_configured": "false",
        "active_user_id": "",
        "current_volume": "70",
        "hotspot_active": "false",
    }
    with Session(get_engine()) as session:
        for key, value in defaults.items():
            existing = session.get(SystemSetting, key)
            if not existing:
                session.add(SystemSetting(key=key, value=value))
        session.commit()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    with Session(get_engine()) as session:
        obj = session.get(SystemSetting, key)
        return obj.value if obj else default


def set_setting(key: str, value: str) -> None:
    with Session(get_engine()) as session:
        obj = session.get(SystemSetting, key)
        if obj:
            obj.value = value
            obj.updated_at = _now()
        else:
            session.add(SystemSetting(key=key, value=value))
        session.commit()


def log_event(source: str, message: str, level: str = "INFO") -> None:
    with Session(get_engine()) as session:
        session.add(SystemEvent(level=level, source=source, message=message))
        session.commit()
        # Ring buffer: keep last 500 events
        count = session.exec(select(SystemEvent)).all()
        if len(count) > 500:
            oldest = session.exec(
                select(SystemEvent).order_by(SystemEvent.id).limit(len(count) - 500)
            ).all()
            for e in oldest:
                session.delete(e)
            session.commit()
