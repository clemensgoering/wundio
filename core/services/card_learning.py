"""
Wundio – Card learning ("play it, then hold the card to the box")

Parents start something on the box (via the Spotify app / Spotify Connect),
then hold a card to the reader. The card is bound to what is playing:

  - Unknown card while something plays → learned automatically
    (can be switched off with the DB setting rfid_auto_learn=false).
  - Learn mode armed from the web UI → the next card is (re)assigned,
    even if it already has a meaning.

Also normalises pasted Spotify share links to spotify: URIs.
"""
import re
import time
from typing import Optional

from sqlmodel import Session, select

from database import RfidTag, get_setting, set_setting

LEARN_SETTING     = "rfid_learn_until"
AUTO_LEARN_KEY    = "rfid_auto_learn"
DEFAULT_LEARN_S   = 60
MAX_LEARN_S       = 300

_SPOTIFY_TYPES = "album|playlist|track|show|episode|artist"
_URI_RE  = re.compile(rf"^spotify:({_SPOTIFY_TYPES}):([A-Za-z0-9]+)$")
_LINK_RE = re.compile(
    rf"^https?://open\.spotify\.com/(?:intl-[a-z]{{2}}(?:-[A-Za-z]{{2}})?/)?"
    rf"({_SPOTIFY_TYPES})/([A-Za-z0-9]+)(?:[/?#].*)?$"
)


def normalize_spotify_uri(value: str) -> Optional[str]:
    """Return a spotify:<type>:<id> URI for a URI or open.spotify.com link, else None."""
    value = (value or "").strip()
    for pattern in (_URI_RE, _LINK_RE):
        m = pattern.match(value)
        if m:
            return f"spotify:{m.group(1)}:{m.group(2)}"
    return None


def learnable_from_state(state) -> Optional[dict]:
    """
    Pick what a card should start from the current playback state:
    the context (album / playlist / show) if it is a shareable one,
    otherwise the current track. None if nothing usable is playing.
    """
    context = normalize_spotify_uri(state.context_uri)
    if context:
        label = state.context_name or state.album_name or state.track_name
        return {"uri": context, "label": label or "Karte"}
    # e.g. "Liked Songs" (spotify:user:…:collection) belongs to the parent's
    # account and would not play on the box account – fall back to the track
    track = normalize_spotify_uri(state.spotify_uri)
    if track:
        return {"uri": track, "label": state.track_name or "Titel"}
    return None


# ── Learn mode ────────────────────────────────────────────────────────────────

def arm(seconds: int = DEFAULT_LEARN_S) -> int:
    """Arm learn mode; returns the unix timestamp it expires at."""
    seconds = max(5, min(MAX_LEARN_S, seconds))
    until = int(time.time()) + seconds
    set_setting(LEARN_SETTING, str(until))
    return until


def disarm() -> None:
    set_setting(LEARN_SETTING, "0")


def seconds_left() -> int:
    try:
        until = int(get_setting(LEARN_SETTING, "0") or 0)
    except ValueError:
        until = 0
    return max(0, until - int(time.time()))


def is_armed() -> bool:
    return seconds_left() > 0


def auto_learn_enabled() -> bool:
    return (get_setting(AUTO_LEARN_KEY, "true") or "true").lower() != "false"


# ── Persistence ───────────────────────────────────────────────────────────────

def bind_card(session: Session, uid: str, spotify_uri: str, label: str) -> RfidTag:
    """Create or overwrite the card as a playback card."""
    tag = session.exec(select(RfidTag).where(RfidTag.uid == uid)).first()
    if tag is None:
        tag = RfidTag(uid=uid)
    tag.tag_type    = "playlist"
    tag.spotify_uri = spotify_uri
    tag.label       = label[:80]
    tag.user_id     = None
    tag.action      = None
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag
