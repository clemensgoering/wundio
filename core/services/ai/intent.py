"""
Wundio – Voice Intent Parser
Maps transcribed text to structured actions without an LLM.
Fast, offline, works on Pi 3.

When a local LLM is available (Pi 5 + Ollama), the LLM handles
complex/ambiguous queries; this parser handles the common cases first.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Intent:
    type: str                          # "volume_up" | "volume_down" | "play" | "pause" |
                                       # "next" | "prev" | "stop" | "greeting" |
                                       # "play_playlist" | "user_switch" | "unknown"
    confidence: float = 1.0
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"type": self.type, "confidence": self.confidence, "params": self.params}


# ── Keyword maps ──────────────────────────────────────────────────────────────

_VOLUME_UP = ["lauter", "lautstärke erhöhen", "mehr lautstärke", "louder", "volume up"]
_VOLUME_DOWN = ["leiser", "lautstärke verringern", "weniger lautstärke", "quieter", "volume down"]
_PLAY = ["spiel", "spielen", "play", "starte", "musik an", "music on", "abspielens"]
_PAUSE = ["pause", "stop", "stopp", "anhalten", "aufhören", "musik aus", "music off"]
_NEXT = ["nächstes", "weiter", "next", "skip", "überspringen"]
_PREV = ["zurück", "vorheriges", "previous", "back"]
_GREETING = ["hallo", "hi", "hey", "guten morgen", "guten tag", "guten abend"]

_PLAYLIST_PATTERNS = [
    r"spiel(?:e|en)?\s+(.+?)(?:\s+playlist|\s+musik|\s+lieder)?$",
    r"ich\s+möchte\s+(.+?)\s+hören",
    r"play\s+(.+)",
]

_USER_PATTERNS = [
    r"ich\s+bin\s+(.+)",
    r"wechsel(?:e|n)?\s+zu\s+(.+)",
    r"nutzer\s+(.+)",
]


def _matches(text: str, keywords: list[str]) -> bool:
    return any(kw in text for kw in keywords)


def parse(text: str) -> Intent:
    """Parse transcribed text into a structured Intent."""
    t = text.lower().strip()

    if not t:
        return Intent(type="unknown", confidence=0.0)

    # Volume
    if _matches(t, _VOLUME_UP):
        amount = _extract_percent(t) or 10
        return Intent(type="volume_up", params={"amount": amount})
    if _matches(t, _VOLUME_DOWN):
        amount = _extract_percent(t) or 10
        return Intent(type="volume_down", params={"amount": amount})

    # Playback control
    if _matches(t, _NEXT):
        return Intent(type="next")
    if _matches(t, _PREV):
        return Intent(type="prev")
    if _matches(t, _PAUSE) and not _matches(t, _PLAY):
        return Intent(type="pause")

    # User switch
    for pat in _USER_PATTERNS:
        m = re.search(pat, t)
        if m:
            return Intent(type="user_switch", params={"name": m.group(1).strip()})

    # Playlist / play
    for pat in _PLAYLIST_PATTERNS:
        m = re.search(pat, t)
        if m:
            query = m.group(1).strip()
            if query and len(query) > 1:
                return Intent(type="play_playlist", params={"query": query})

    if _matches(t, _PLAY):
        return Intent(type="play")

    # Greeting
    if _matches(t, _GREETING):
        return Intent(type="greeting")

    return Intent(type="unknown", confidence=0.4, params={"raw": t})


def _extract_percent(text: str) -> Optional[int]:
    """Extract a percentage or number word from text."""
    m = re.search(r"(\d+)\s*%", text)
    if m:
        return int(m.group(1))
    words = {
        "zehn": 10, "zwanzig": 20, "dreißig": 30,
        "ten": 10, "twenty": 20, "thirty": 30,
    }
    for word, val in words.items():
        if word in text:
            return val
    return None
