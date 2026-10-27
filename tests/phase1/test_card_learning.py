"""
Phase 1 – Card learning ("play it, then hold the card to the box")
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, select


def _state(playing=True, context_uri="", context_name="", track_uri="", track_name="", album=""):
    from services.spotify import PlaybackState
    s = PlaybackState()
    s.playing      = playing
    s.context_uri  = context_uri
    s.context_name = context_name
    s.spotify_uri  = track_uri
    s.track_name   = track_name
    s.album_name   = album
    return s


def _scan(uid: str, state):
    """Run main._on_rfid_scan with a fake Spotify service returning `state`."""
    import main
    fake = MagicMock()
    fake.refresh_state.return_value = state
    fake.play_uri_async = MagicMock()

    async def _play(uri):
        return True
    fake.play_uri_async.side_effect = _play
    with patch.object(main, "get_spotify_service", return_value=fake):
        asyncio.run(main._on_rfid_scan(uid))
    return fake


def _tag(uid: str):
    from database import get_engine, RfidTag
    with Session(get_engine()) as s:
        return s.exec(select(RfidTag).where(RfidTag.uid == uid)).first()


# ── Link normalisation ────────────────────────────────────────────────────────

class TestNormalize:
    @pytest.mark.parametrize("value,expected", [
        ("spotify:album:4aawyAB9vmqN3uQ7FjRGTy", "spotify:album:4aawyAB9vmqN3uQ7FjRGTy"),
        ("https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy?si=abc123",
         "spotify:album:4aawyAB9vmqN3uQ7FjRGTy"),
        ("https://open.spotify.com/intl-de/playlist/37i9dQZF1DX0XUsuxWHRQd",
         "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd"),
        ("  https://open.spotify.com/show/5CfCWKI5pZ28U0uOzXkDHe  ",
         "spotify:show:5CfCWKI5pZ28U0uOzXkDHe"),
    ])
    def test_valid(self, value, expected):
        from services.card_learning import normalize_spotify_uri
        assert normalize_spotify_uri(value) == expected

    @pytest.mark.parametrize("value", [
        "", "hello", "https://example.com/album/abc",
        "spotify:user:someone:collection", "spotify:album:",
    ])
    def test_invalid(self, value):
        from services.card_learning import normalize_spotify_uri
        assert normalize_spotify_uri(value) is None


class TestLearnableFromState:
    def test_prefers_context(self):
        from services.card_learning import learnable_from_state
        t = learnable_from_state(_state(
            context_uri="spotify:album:abc", context_name="Die drei ??? Folge 1",
            track_uri="spotify:track:t1", track_name="Kapitel 1",
        ))
        assert t == {"uri": "spotify:album:abc", "label": "Die drei ??? Folge 1"}

    def test_liked_songs_falls_back_to_track(self):
        from services.card_learning import learnable_from_state
        t = learnable_from_state(_state(
            context_uri="spotify:user:parent:collection",
            track_uri="spotify:track:t1", track_name="Lied",
        ))
        assert t == {"uri": "spotify:track:t1", "label": "Lied"}

    def test_nothing_usable(self):
        from services.card_learning import learnable_from_state
        assert learnable_from_state(_state()) is None


# ── Learn mode ────────────────────────────────────────────────────────────────

class TestLearnMode:
    def test_arm_and_disarm(self, tmp_db):
        from services import card_learning
        assert card_learning.is_armed() is False
        card_learning.arm(30)
        assert card_learning.is_armed() is True
        assert 25 <= card_learning.seconds_left() <= 30
        card_learning.disarm()
        assert card_learning.is_armed() is False

    def test_arm_is_clamped(self, tmp_db):
        from services import card_learning
        card_learning.arm(99999)
        assert card_learning.seconds_left() <= card_learning.MAX_LEARN_S


# ── RFID scan flow ────────────────────────────────────────────────────────────

class TestScanLearning:
    def test_unknown_card_learned_while_playing(self, tmp_db):
        _scan("NEWCARD", _state(context_uri="spotify:album:abc", context_name="Bibi Blocksberg"))
        tag = _tag("NEWCARD")
        assert tag is not None
        assert tag.tag_type == "playlist"
        assert tag.spotify_uri == "spotify:album:abc"
        assert tag.label == "Bibi Blocksberg"

    def test_unknown_card_not_learned_when_idle(self, tmp_db):
        _scan("IDLECARD", _state(playing=False, context_uri="spotify:album:abc"))
        assert _tag("IDLECARD") is None

    def test_auto_learn_can_be_disabled(self, tmp_db):
        from database import set_setting
        set_setting("rfid_auto_learn", "false")
        _scan("NOAUTO", _state(context_uri="spotify:album:abc"))
        assert _tag("NOAUTO") is None

    def test_known_card_plays_instead_of_learning(self, tmp_db):
        from database import get_engine, RfidTag
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="KNOWN", tag_type="playlist", spotify_uri="spotify:album:old", label="Alt"))
            s.commit()
        fake = _scan("KNOWN", _state(context_uri="spotify:album:new"))
        assert _tag("KNOWN").spotify_uri == "spotify:album:old"
        fake.play_uri_async.assert_called_once_with("spotify:album:old")

    def test_armed_overwrites_existing_card_and_disarms(self, tmp_db):
        from database import get_engine, RfidTag
        from services import card_learning
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="KIDCARD", tag_type="user", user_id=None, label="Lena"))
            s.commit()
        card_learning.arm(60)
        _scan("KIDCARD", _state(context_uri="spotify:playlist:p1", context_name="Schlaflieder"))
        tag = _tag("KIDCARD")
        assert tag.tag_type == "playlist"
        assert tag.spotify_uri == "spotify:playlist:p1"
        assert card_learning.is_armed() is False

    def test_armed_but_idle_keeps_mode(self, tmp_db):
        from services import card_learning
        card_learning.arm(60)
        _scan("WAITCARD", _state(playing=False))
        assert _tag("WAITCARD") is None
        assert card_learning.is_armed() is True


# ── API ───────────────────────────────────────────────────────────────────────

class TestLearnApi:
    def test_learn_roundtrip(self, api_client):
        assert api_client.get("/api/rfid/learn").json()["armed"] is False
        r = api_client.post("/api/rfid/learn", json={"seconds": 30})
        assert r.status_code == 200 and r.json()["armed"] is True
        d = api_client.get("/api/rfid/learn").json()
        assert d["armed"] is True
        assert set(d) == {"armed", "seconds_left", "auto_learn", "now_playing"}
        r = api_client.delete("/api/rfid/learn")
        assert r.status_code == 200 and r.json()["armed"] is False

    def test_assign_accepts_share_link(self, api_client):
        r = api_client.post("/api/rfid/assign", json={
            "uid": "LINK1", "label": "Hörspiel", "tag_type": "playlist",
            "spotify_uri": "https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy?si=x",
        })
        assert r.status_code == 200
        assert r.json()["spotify_uri"] == "spotify:album:4aawyAB9vmqN3uQ7FjRGTy"

    def test_assign_rejects_garbage(self, api_client):
        r = api_client.post("/api/rfid/assign", json={
            "uid": "BAD1", "label": "x", "tag_type": "playlist", "spotify_uri": "kein link",
        })
        assert r.status_code == 422
        assert "Spotify" in r.json()["detail"]

    def test_delete_tag_still_works(self, api_client):
        api_client.post("/api/rfid/assign", json={
            "uid": "DEL1", "label": "x", "tag_type": "action", "action": "stop",
        })
        assert api_client.delete("/api/rfid/DEL1").status_code == 200
