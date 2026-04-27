"""
tests/phase0/test_system_api.py – System, Settings, and RFID API endpoints.
"""
import subprocess


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

    def test_restart_returns_ok(self, api_client, monkeypatch):
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        r = api_client.post("/api/system/restart")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_restart_response_is_json(self, api_client, monkeypatch):
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        r = api_client.post("/api/system/restart")
        assert r.headers["content-type"].startswith("application/json")


class TestSettingsApi:
    def test_env_schema_includes_rfid_type(self, api_client):
        schema = api_client.get("/api/settings/env/schema").json()
        assert "RFID_TYPE" in schema

    def test_env_schema_includes_audio_type(self, api_client):
        schema = api_client.get("/api/settings/env/schema").json()
        assert "AUDIO_TYPE" in schema

    def test_env_schema_includes_display_type(self, api_client):
        schema = api_client.get("/api/settings/env/schema").json()
        assert "DISPLAY_TYPE" in schema

    def test_env_all_returns_list(self, api_client):
        r = api_client.get("/api/settings/env/all")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_env_all_has_rfid_entry(self, api_client):
        keys = [e["key"] for e in api_client.get("/api/settings/env/all").json()]
        assert "RFID_TYPE" in keys

    def test_env_all_has_audio_entry(self, api_client):
        keys = [e["key"] for e in api_client.get("/api/settings/env/all").json()]
        assert "AUDIO_TYPE" in keys


class TestRfidApi:
    def test_assign_and_list(self, api_client):
        api_client.post("/api/rfid/assign", json={
            "uid": "AABBCCDD", "label": "Test",
            "tag_type": "action", "action": "stop",
        })
        uids = [t["uid"] for t in api_client.get("/api/rfid/").json()]
        assert "AABBCCDD" in uids

    def test_reassign(self, api_client):
        for action in ("stop", "play"):
            api_client.post("/api/rfid/assign", json={
                "uid": "DEAD", "label": "X",
                "tag_type": "action", "action": action,
            })
        tag = next(t for t in api_client.get("/api/rfid/").json() if t["uid"] == "DEAD")
        assert tag["action"] == "play"

    def test_delete(self, api_client):
        api_client.post("/api/rfid/assign", json={
            "uid": "BEEF", "label": "Del",
            "tag_type": "action", "action": "stop",
        })
        assert api_client.delete("/api/rfid/BEEF").status_code == 200
        assert all(t["uid"] != "BEEF" for t in api_client.get("/api/rfid/").json())

    def test_delete_nonexistent_404(self, api_client):
        assert api_client.delete("/api/rfid/NOTEXIST").status_code == 404

    def test_mock_scan(self, api_client):
        r = api_client.post("/api/rfid/mock-scan/TESTUID")
        assert r.json()["scanned"] == "TESTUID"