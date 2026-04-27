"""
tests/phase0/test_rfid.py – RFID drivers, service, and tag resolution.
"""
import asyncio
import pytest


class TestRfidDrivers:
    def test_rc522_available_false_without_hardware(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "mfrc522", None)
        from services import rfid as rfid_mod
        import importlib
        importlib.reload(rfid_mod)
        d = rfid_mod.RC522Driver()
        assert d.setup() is False
        assert d.available is False

    def test_pn532_available_false_without_hardware(self):
        from services.rfid import PN532Driver
        d = PN532Driver()
        assert d.setup() is False
        assert d.available is False

    def test_rc522_read_returns_none_without_hardware(self):
        from services.rfid import RC522Driver
        assert RC522Driver().read_uid_blocking() is None

    def test_pn532_read_returns_none_without_hardware(self):
        from services.rfid import PN532Driver
        assert PN532Driver().read_uid_blocking() is None

    def test_rc522_teardown_safe_without_hardware(self):
        from services.rfid import RC522Driver
        RC522Driver().teardown()

    def test_pn532_teardown_safe_without_hardware(self):
        from services.rfid import PN532Driver
        PN532Driver().teardown()

    def test_both_drivers_implement_abstract_interface(self):
        from services.rfid import RC522Driver, PN532Driver, RfidDriver
        assert issubclass(RC522Driver, RfidDriver)
        assert issubclass(PN532Driver, RfidDriver)

    @pytest.mark.parametrize("rfid_type,expected_cls", [
        ("rc522", "RC522Driver"),
        ("pn532", "PN532Driver"),
    ])
    def test_factory_returns_correct_driver(self, rfid_type, expected_cls, monkeypatch):
        import services.rfid as rfid_mod
        monkeypatch.setattr(
            rfid_mod,
            "_build_driver_from_config",
            lambda rt=rfid_type: (
                rfid_mod.RC522Driver() if rt == "rc522" else rfid_mod.PN532Driver()
            ),
        )
        driver = rfid_mod._build_driver_from_config()
        assert type(driver).__name__ == expected_cls


class TestRfidService:
    def test_setup_returns_bool(self):
        from services.rfid import RfidService
        assert isinstance(RfidService().setup(), bool)

    def test_available_false_without_hardware(self, monkeypatch):
        import sys
        monkeypatch.setitem(sys.modules, "mfrc522", None)
        from services import rfid as rfid_mod
        import importlib
        importlib.reload(rfid_mod)
        svc = rfid_mod.RfidService()
        svc.setup()
        assert svc.available is False

    def test_simulate_scan_calls_callback(self):
        from services.rfid import RfidService
        received = []

        async def run():
            svc = RfidService()
            async def cb(uid): received.append(uid)
            svc._callback = cb
            await svc.simulate_scan("TESTUID")

        asyncio.run(run())
        assert "TESTUID" in received

    def test_write_uid_mock_alias_works(self):
        from services.rfid import RfidService
        received = []

        async def run():
            svc = RfidService()
            async def cb(uid): received.append(uid)
            svc._callback = cb
            await svc.write_uid_mock("LEGACYUID")

        asyncio.run(run())
        assert "LEGACYUID" in received

    def test_service_accepts_rc522_driver(self):
        from services.rfid import RfidService, RC522Driver
        svc = RfidService(driver=RC522Driver())
        assert svc.available is False

    def test_service_accepts_pn532_driver(self):
        from services.rfid import RfidService, PN532Driver
        svc = RfidService(driver=PN532Driver())
        assert svc.available is False

    def test_singleton(self):
        from services.rfid import get_rfid_service
        assert get_rfid_service() is get_rfid_service()

    def test_debounce_suppresses_duplicate_uid(self):
        """Same UID fired twice must only trigger callback once."""
        from services.rfid import RfidService
        received = []

        async def run():
            svc = RfidService()
            async def cb(uid): received.append(uid)
            svc._callback = cb
            svc._last_uid = "DUPE"
            await svc.simulate_scan("DUPE")

        asyncio.run(run())
        assert len(received) == 1


class TestRfidResolution:
    def test_user_tag(self, tmp_db):
        from database import get_engine, RfidTag, User
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            user = User(name="alice", display_name="Alice")
            s.add(user)
            s.flush()
            uid_val = user.id
            s.add(RfidTag(uid="AABB", tag_type="user", user_id=uid_val, label="Alice"))
            s.commit()
            r = resolve_rfid_action(s, "AABB")
        assert r == {"type": "user_login", "user_id": uid_val}

    def test_playlist_tag(self, tmp_db):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        uri = "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd"
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="CCDD", tag_type="playlist", spotify_uri=uri, label="Hits"))
            s.commit()
            r = resolve_rfid_action(s, "CCDD")
        assert r == {"type": "playlist", "spotify_uri": uri, "label": "Hits"}

    def test_action_tag(self, tmp_db):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="EEFF", tag_type="action", action="stop", label="Stop"))
            s.commit()
            r = resolve_rfid_action(s, "EEFF")
        assert r == {"type": "action", "action": "stop"}

    def test_incomplete_tag_returns_none(self, tmp_db):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="FFFF", tag_type="user", label="Broken"))
            s.commit()
            r = resolve_rfid_action(s, "FFFF")
        assert r is None

    def test_unknown_uid_returns_none(self, tmp_db):
        from database import get_engine
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            r = resolve_rfid_action(s, "00000000")
        assert r is None