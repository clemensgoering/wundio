"""
Phase 0 – Core Tests
Hardware detection, database, RFID resolution, display, API endpoints.
No Raspberry Pi hardware required.
"""
import pytest


# ── Hardware Detection ────────────────────────────────────────────────────────

class TestHardwareDetection:
    def test_returns_profile(self):
        from services.hardware import detect
        p = detect()
        assert p.model is not None
        assert isinstance(p.ram_mb, int)
        assert isinstance(p.pi_generation, int)

    def test_to_dict_structure(self):
        from services.hardware import detect
        d = detect().to_dict()
        assert "features" in d
        for key in ("spotify", "rfid", "display_oled", "buttons", "ai_local", "ai_cloud"):
            assert key in d["features"]

    def test_dev_machine_disables_ai_local(self):
        from services.hardware import detect
        p = detect()
        if not p.is_pi:
            assert p.feature_ai_local is False

    @pytest.mark.parametrize("gen,ram,expect_ai_local", [
        (3, 1024,  False),
        (4, 4096,  False),
        (5, 4096,  False),
        (5, 8192,  True),
    ])
    def test_feature_flags_by_generation(self, gen, ram, expect_ai_local):
        from services.hardware import HardwareProfile
        p = HardwareProfile(model=f"Raspberry Pi {gen}", ram_mb=ram,
                            is_pi=True, pi_generation=gen)
        p.feature_spotify = True; p.feature_rfid = True
        p.feature_display_oled = True; p.feature_buttons = True
        if gen >= 4:
            p.feature_games_advanced = True; p.feature_ai_cloud = True
        if gen >= 5 and ram >= 7000:
            p.feature_ai_local = True
        assert p.feature_ai_local == expect_ai_local

    @pytest.mark.parametrize("gen,expect_cloud", [(3, False), (4, True), (5, True)])
    def test_cloud_ai_gating(self, gen, expect_cloud):
        from services.hardware import HardwareProfile
        p = HardwareProfile(model=f"Raspberry Pi {gen}", ram_mb=4096,
                            is_pi=True, pi_generation=gen)
        p.feature_ai_cloud = gen >= 4
        assert p.feature_ai_cloud == expect_cloud


# ── Database ──────────────────────────────────────────────────────────────────

class TestDatabase:
    def test_get_set_roundtrip(self, tmp_db):
        from database import get_setting, set_setting
        set_setting("mykey", "myvalue")
        assert get_setting("mykey") == "myvalue"

    def test_overwrite_setting(self, tmp_db):
        from database import get_setting, set_setting
        set_setting("k", "v1"); set_setting("k", "v2")
        assert get_setting("k") == "v2"

    def test_missing_key_returns_default(self, tmp_db):
        from database import get_setting
        assert get_setting("nonexistent", "fallback") == "fallback"
        assert get_setting("nonexistent") == ""

    def test_default_seeds_exist(self, tmp_db):
        from database import get_setting
        assert get_setting("setup_complete") == "false"
        assert get_setting("wifi_configured") == "false"
        assert get_setting("hotspot_active") == "false"

    def test_log_event_stored(self, tmp_db):
        from database import log_event, get_engine, SystemEvent
        from sqlmodel import Session, select
        log_event("test", "hello world", level="WARN")
        with Session(get_engine()) as s:
            events = s.exec(select(SystemEvent)).all()
        assert any(e.message == "hello world" and e.level == "WARN" for e in events)

    def test_log_event_ring_buffer(self, tmp_db):
        from database import log_event, get_engine, SystemEvent
        from sqlmodel import Session, select
        for i in range(510):
            log_event("test", f"event {i}")
        with Session(get_engine()) as s:
            count = len(s.exec(select(SystemEvent)).all())
        assert count <= 500

    def test_create_user(self, tmp_db):
        from database import get_engine, User
        from sqlmodel import Session, select
        with Session(get_engine()) as s:
            u = User(name="alice", display_name="Alice", volume=80)
            s.add(u); s.commit()
            result = s.exec(select(User).where(User.name == "alice")).first()
        assert result.display_name == "Alice"
        assert result.volume == 80
        assert result.is_active is True


# ── RFID Resolution ───────────────────────────────────────────────────────────

class TestRfidResolution:
    def test_unknown_uid(self, tmp_db):
        from database import get_engine
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            assert resolve_rfid_action(s, "DEADBEEF") is None

    def test_user_login_tag(self, tmp_db):
        from database import get_engine, User, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        with Session(get_engine()) as s:
            u = User(name="bob", display_name="Bob")
            s.add(u); s.commit(); s.refresh(u); uid = u.id
            s.add(RfidTag(uid="AABB", tag_type="user", user_id=uid, label="Bob"))
            s.commit()
        with Session(get_engine()) as s:
            r = resolve_rfid_action(s, "AABB")
        assert r == {"type": "user_login", "user_id": uid}

    def test_playlist_tag(self, tmp_db):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session
        uri = "spotify:playlist:37i9dQZF1DX0XUsuxWHRQd"
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="CCDD", tag_type="playlist", spotify_uri=uri, label="Hits"))
            s.commit()
            r = resolve_rfid_action(s, "CCDD")
        assert r == {"type": "playlist", "spotify_uri": uri}

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


# ── Display ───────────────────────────────────────────────────────────────────

class TestDisplay:
    def test_availability_consistent(self):
        from services.display import OledDisplay
        d = OledDisplay(); result = d.setup()
        assert result == d._available

    def test_all_screens_safe_without_hardware(self):
        from services.display import OledDisplay
        d = OledDisplay(); d.setup()
        d.show_boot("0.1.0"); d.show_idle("Bereit")
        d.show_user_login("Max", "🎵")
        d.show_playing("Song", "Artist", "Max")
        d.show_setup("Wundio-Setup", "192.168.50.1")
        d.show_error("Fehler!"); d.clear(); d.teardown()

    def test_singleton(self):
        from services.display import get_display
        assert get_display() is get_display()


# ── RFID Service ──────────────────────────────────────────────────────────────

class TestRfidService:
    def test_setup_returns_bool(self):
        from services.rfid import RfidService
        assert isinstance(RfidService().setup(), bool)

    def test_mock_scan_calls_callback(self):
        import asyncio
        from services.rfid import RfidService
        received = []
        async def run():
            svc = RfidService()
            async def cb(uid): received.append(uid)
            svc._callback = cb
            await svc.write_uid_mock("TESTUID")
        asyncio.run(run())
        assert "TESTUID" in received

    def test_singleton(self):
        from services.rfid import get_rfid_service
        assert get_rfid_service() is get_rfid_service()


# ── System API ────────────────────────────────────────────────────────────────

class TestSystemApi:
    def test_health(self, api_client):
        r = api_client.get("/api/system/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_status_shape(self, api_client):
        d = api_client.get("/api/system/status").json()
        for key in ("app_name", "version", "setup_complete", "features", "hardware"):
            assert key in d

    def test_complete_setup(self, api_client):
        from database import get_setting
        api_client.post("/api/system/complete-setup")
        assert get_setting("setup_complete") == "true"


# ── Settings API ──────────────────────────────────────────────────────────────

class TestSettingsApi:
    def test_write_and_read(self, api_client):
        api_client.put("/api/settings/test_key", json={"value": "hello"})
        r = api_client.get("/api/settings/test_key")
        assert r.json()["value"] == "hello"

    def test_overwrite(self, api_client):
        api_client.put("/api/settings/vol", json={"value": "70"})
        api_client.put("/api/settings/vol", json={"value": "85"})
        assert api_client.get("/api/settings/vol").json()["value"] == "85"


# ── Users API ─────────────────────────────────────────────────────────────────

class TestUsersApi:
    def test_create(self, api_client):
        r = api_client.post("/api/users/", json={"name": "max", "display_name": "Max"})
        assert r.status_code == 200
        assert r.json()["name"] == "max"

    def test_list(self, api_client):
        api_client.post("/api/users/", json={"name": "a", "display_name": "A"})
        api_client.post("/api/users/", json={"name": "b", "display_name": "B"})
        names = [u["name"] for u in api_client.get("/api/users/").json()]
        assert "a" in names and "b" in names

    def test_update(self, api_client):
        uid = api_client.post("/api/users/", json={"name": "c", "display_name": "Old"}).json()["id"]
        r = api_client.patch(f"/api/users/{uid}", json={"display_name": "New", "volume": 90})
        assert r.json()["display_name"] == "New"
        assert r.json()["volume"] == 90

    def test_soft_delete(self, api_client):
        uid = api_client.post("/api/users/", json={"name": "d", "display_name": "D"}).json()["id"]
        api_client.delete(f"/api/users/{uid}")
        active = [u["id"] for u in api_client.get("/api/users/").json()]
        assert uid not in active

    def test_update_nonexistent_404(self, api_client):
        assert api_client.patch("/api/users/9999", json={"display_name": "Ghost"}).status_code == 404


# ── RFID API ──────────────────────────────────────────────────────────────────

class TestRfidApi:
    def test_assign_and_list(self, api_client):
        api_client.post("/api/rfid/assign", json={
            "uid": "AABBCCDD", "label": "Test", "tag_type": "action", "action": "stop"})
        uids = [t["uid"] for t in api_client.get("/api/rfid/").json()]
        assert "AABBCCDD" in uids

    def test_reassign(self, api_client):
        for action in ("stop", "play"):
            api_client.post("/api/rfid/assign", json={
                "uid": "DEAD", "label": "X", "tag_type": "action", "action": action})
        r = api_client.get("/api/rfid/").json()
        tag = next(t for t in r if t["uid"] == "DEAD")
        assert tag["action"] == "play"

    def test_delete(self, api_client):
        api_client.post("/api/rfid/assign", json={
            "uid": "BEEF", "label": "Del", "tag_type": "action", "action": "stop"})
        assert api_client.delete("/api/rfid/BEEF").status_code == 200
        assert all(t["uid"] != "BEEF" for t in api_client.get("/api/rfid/").json())

    def test_delete_nonexistent_404(self, api_client):
        assert api_client.delete("/api/rfid/NOTEXIST").status_code == 404

    def test_mock_scan(self, api_client):
        r = api_client.post("/api/rfid/mock-scan/TESTUID")
        assert r.json()["scanned"] == "TESTUID"
