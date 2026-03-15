"""
Wundio – Phase 0 Tests
Run with: make test  (no Pi hardware required)
"""

import sys
import os
import pytest

# Make core importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../core"))

# Stub out RPi dependencies before importing anything
import unittest.mock as mock
sys.modules.setdefault("RPi", mock.MagicMock())
sys.modules.setdefault("RPi.GPIO", mock.MagicMock())
sys.modules.setdefault("spidev", mock.MagicMock())
sys.modules.setdefault("mfrc522", mock.MagicMock())
sys.modules.setdefault("luma", mock.MagicMock())
sys.modules.setdefault("luma.core", mock.MagicMock())
sys.modules.setdefault("luma.core.interface", mock.MagicMock())
sys.modules.setdefault("luma.core.interface.serial", mock.MagicMock())
sys.modules.setdefault("luma.core.render", mock.MagicMock())
sys.modules.setdefault("luma.oled", mock.MagicMock())
sys.modules.setdefault("luma.oled.device", mock.MagicMock())


# ── Hardware Detection ────────────────────────────────────────────────────────

class TestHardwareDetection:
    def test_detect_returns_profile(self):
        from services.hardware import detect
        profile = detect()
        assert profile is not None
        assert isinstance(profile.ram_mb, int)
        assert isinstance(profile.pi_generation, int)

    def test_non_pi_enables_dev_features(self):
        from services.hardware import detect
        profile = detect()
        if not profile.is_pi:
            # On dev machine: basic features on, ai_local off
            assert profile.feature_spotify is True
            assert profile.feature_ai_local is False

    def test_to_dict_has_features(self):
        from services.hardware import detect
        d = detect().to_dict()
        assert "features" in d
        assert "spotify" in d["features"]


# ── Database ──────────────────────────────────────────────────────────────────

class TestDatabase:
    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        from database import init_db, _seed_defaults
        import database
        database._engine = None  # reset singleton
        init_db(str(tmp_path / "test.db"))
        yield
        database._engine = None

    def test_get_set_setting(self):
        from database import get_setting, set_setting
        set_setting("test_key", "hello")
        assert get_setting("test_key") == "hello"

    def test_default_settings_exist(self):
        from database import get_setting
        assert get_setting("setup_complete") == "false"
        assert get_setting("wifi_configured") == "false"

    def test_log_event(self):
        from database import log_event, get_engine, SystemEvent
        from sqlmodel import Session, select
        log_event("test", "hello world")
        with Session(get_engine()) as session:
            events = session.exec(select(SystemEvent)).all()
        assert any(e.message == "hello world" for e in events)

    def test_create_user(self):
        from database import get_engine, User
        from sqlmodel import Session, select
        with Session(get_engine()) as session:
            user = User(name="alice", display_name="Alice")
            session.add(user)
            session.commit()
            result = session.exec(select(User).where(User.name == "alice")).first()
        assert result is not None
        assert result.display_name == "Alice"


# ── RFID Tag Resolution ───────────────────────────────────────────────────────

class TestRfidResolution:
    @pytest.fixture(autouse=True)
    def setup_db(self, tmp_path):
        from database import init_db
        import database
        database._engine = None
        init_db(str(tmp_path / "test.db"))
        yield
        database._engine = None

    def test_unknown_uid_returns_none(self):
        from database import get_engine
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as session:
            result = resolve_rfid_action(session, "DEADBEEF")
        assert result is None

    def test_user_tag_resolves(self):
        from database import get_engine, User, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        # Create user and tag, capture id while session is open
        with Session(get_engine()) as session:
            user = User(name="bob", display_name="Bob")
            session.add(user)
            session.commit()
            session.refresh(user)
            user_id = user.id          # capture before session closes
            tag = RfidTag(uid="AABBCCDD", tag_type="user", user_id=user_id, label="Bob's card")
            session.add(tag)
            session.commit()

        with Session(get_engine()) as session:
            result = resolve_rfid_action(session, "AABBCCDD")

        assert result["type"] == "user_login"
        assert result["user_id"] == user_id

    def test_playlist_tag_resolves(self):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as session:
            tag = RfidTag(
                uid="11223344",
                tag_type="playlist",
                spotify_uri="spotify:playlist:37i9dQZF1DX0XUsuxWHRQd",
                label="Schlagermusik"
            )
            session.add(tag)
            session.commit()
            result = resolve_rfid_action(session, "11223344")
        assert result["type"] == "playlist"
        assert "spotify" in result["spotify_uri"]


# ── Display (no hardware) ─────────────────────────────────────────────────────

class TestDisplay:
    def test_setup_result_matches_availability(self):
        from services.display import OledDisplay
        d = OledDisplay()
        result = d.setup()
        # Whatever setup() returns must match internal _available flag
        assert result == d._available

    def test_methods_dont_crash_without_hardware(self):
        from services.display import OledDisplay
        d = OledDisplay()
        d.setup()
        # All these should be safe no-ops
        d.show_boot("0.1.0")
        d.show_idle()
        d.show_user_login("Alice")
        d.show_playing("Song", "Artist")
        d.show_setup("MyNet", "192.168.1.1")
        d.show_error("Test error")
        d.clear()
        d.teardown()


# ── API (FastAPI TestClient) ──────────────────────────────────────────────────

class TestApi:
    @pytest.fixture(autouse=True)
    def setup_app(self, tmp_path):
        import database
        database._engine = None
        db_path = str(tmp_path / "test.db")
        os.environ["DB_PATH"] = db_path

        # Init DB before app routes are called (lifespan not triggered in TestClient)
        database.init_db(db_path)

        from fastapi.testclient import TestClient
        from main import app
        # Use context manager to trigger lifespan startup/shutdown
        with TestClient(app, raise_server_exceptions=False) as client:
            self.client = client
            yield
        database._engine = None

    def test_health(self):
        r = self.client.get("/api/system/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_status(self):
        r = self.client.get("/api/system/status")
        assert r.status_code == 200
        data = r.json()
        assert "features" in data
        assert "version" in data

    def test_create_and_list_users(self):
        r = self.client.post("/api/users/", json={
            "name": "max",
            "display_name": "Max Mustermann"
        })
        assert r.status_code == 200
        uid = r.json()["id"]

        r = self.client.get("/api/users/")
        assert r.status_code == 200
        names = [u["name"] for u in r.json()]
        assert "max" in names
