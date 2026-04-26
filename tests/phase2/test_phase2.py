"""
Phase 2 – Multi-User, WiFi & Integration Tests
All tests run without Pi hardware.
"""
import pytest


# ── Multi-User Profile Flows ──────────────────────────────────────────────────

class TestMultiUserFlow:
    """Full lifecycle: create → assign RFID → login via tag → volume restored."""

    def test_create_two_children(self, api_client):
        r1 = api_client.post("/api/users/", json={"name": "lena",  "display_name": "Lena",  "volume": 60})
        r2 = api_client.post("/api/users/", json={"name": "jonas", "display_name": "Jonas", "volume": 80})
        assert r1.status_code == 200
        assert r2.status_code == 200
        users = api_client.get("/api/users/").json()
        names = [u["name"] for u in users]
        assert "lena" in names and "jonas" in names

    def test_rfid_user_login_sets_active_and_volume(self, api_client):
        # Create user
        uid = api_client.post("/api/users/", json={
            "name": "lena", "display_name": "Lena", "volume": 65
        }).json()["id"]

        # Assign RFID tag
        api_client.post("/api/rfid/assign", json={
            "uid": "AA11BB22", "label": "Lena RFID",
            "tag_type": "user", "user_id": uid
        })

        # Activate via playback API (simulating RFID dispatch)
        r = api_client.post("/api/playback/active-user", json={"user_id": uid})
        assert r.status_code == 200
        assert r.json()["volume"] == 65
        assert r.json()["active_user"] == "Lena"

        # Setting persisted
        from database import get_setting
        assert get_setting("active_user_id") == str(uid)

    def test_volume_persisted_per_user(self, api_client):
        """Each child retains its own volume setting."""
        id1 = api_client.post("/api/users/", json={"name": "a", "display_name": "A", "volume": 40}).json()["id"]
        id2 = api_client.post("/api/users/", json={"name": "b", "display_name": "B", "volume": 90}).json()["id"]

        api_client.post("/api/playback/active-user", json={"user_id": id1})
        state1 = api_client.get("/api/playback/state").json()

        api_client.post("/api/playback/active-user", json={"user_id": id2})
        state2 = api_client.get("/api/playback/state").json()

        assert state1["volume"] == 40
        assert state2["volume"] == 90

    def test_soft_delete_removes_from_list(self, api_client):
        uid = api_client.post("/api/users/", json={"name": "x", "display_name": "X"}).json()["id"]
        api_client.delete(f"/api/users/{uid}")
        remaining = [u["id"] for u in api_client.get("/api/users/").json()]
        assert uid not in remaining

    def test_user_update_persists(self, api_client):
        uid = api_client.post("/api/users/", json={
            "name": "y", "display_name": "Old Name", "volume": 50
        }).json()["id"]
        api_client.patch(f"/api/users/{uid}", json={"display_name": "New Name", "volume": 75})
        users = api_client.get("/api/users/").json()
        user  = next(u for u in users if u["id"] == uid)
        assert user["display_name"] == "New Name"
        assert user["volume"] == 75

    def test_playlist_update_for_user(self, api_client):
        uid = api_client.post("/api/users/", json={"name": "z", "display_name": "Z"}).json()["id"]
        api_client.patch(f"/api/users/{uid}", json={
            "spotify_playlist_id":   "37i9dQZF1DX0XUsuxWHRQd",
            "spotify_playlist_name": "Hits für Kinder",
        })
        users = api_client.get("/api/users/").json()
        user  = next(u for u in users if u["id"] == uid)
        assert user["spotify_playlist_name"] == "Hits für Kinder"


# ── RFID Full Flows ───────────────────────────────────────────────────────────

class TestRfidIntegration:
    def test_full_assign_reassign_delete_cycle(self, api_client):
        # Assign
        api_client.post("/api/rfid/assign", json={
            "uid": "CYCLE01", "label": "v1",
            "tag_type": "action", "action": "stop"
        })
        # Reassign same UID
        api_client.post("/api/rfid/assign", json={
            "uid": "CYCLE01", "label": "v2",
            "tag_type": "action", "action": "vol_up"
        })
        tags = api_client.get("/api/rfid/").json()
        tag  = next(t for t in tags if t["uid"] == "CYCLE01")
        assert tag["action"] == "vol_up"
        assert tag["label"]  == "v2"

        # Delete
        api_client.delete("/api/rfid/CYCLE01")
        tags2 = api_client.get("/api/rfid/").json()
        assert all(t["uid"] != "CYCLE01" for t in tags2)

    def test_multiple_tag_types_coexist(self, api_client):
        user_id = api_client.post("/api/users/", json={"name": "co", "display_name": "Co"}).json()["id"]
        api_client.post("/api/rfid/assign", json={"uid": "U001", "label": "User",     "tag_type": "user",     "user_id": user_id})
        api_client.post("/api/rfid/assign", json={"uid": "P001", "label": "Playlist", "tag_type": "playlist", "spotify_uri": "spotify:playlist:abc"})
        api_client.post("/api/rfid/assign", json={"uid": "A001", "label": "Action",   "tag_type": "action",   "action": "stop"})

        tags  = api_client.get("/api/rfid/").json()
        types = {t["uid"]: t["tag_type"] for t in tags}
        assert types.get("U001") == "user"
        assert types.get("P001") == "playlist"
        assert types.get("A001") == "action"

    def test_mock_scan_unknown_tag_does_not_crash(self, api_client):
        r = api_client.post("/api/rfid/mock-scan/FFFFFF00")
        assert r.status_code == 200


# ── WiFi API ──────────────────────────────────────────────────────────────────

class TestWifiApi:
    def test_status_endpoint(self, api_client):
        r = api_client.get("/api/wifi/status")
        assert r.status_code == 200
        d = r.json()
        assert "configured" in d
        assert "ssid" in d

    def test_configure_wifi_mock(self, api_client):
        """Configure WiFi in mock mode (no root → permission error is caught)."""
        r = api_client.post("/api/wifi/configure", json={
            "ssid": "MyHomeNet", "password": "secret123"
        })
        assert r.status_code == 200
        assert r.json()["ssid"] == "MyHomeNet"

    def test_configure_sets_settings(self, api_client):
        from database import get_setting
        api_client.post("/api/wifi/configure", json={"ssid": "TestNet", "password": "pw"})
        assert get_setting("wifi_configured") == "true"
        assert get_setting("wifi_ssid") == "TestNet"

    def test_configure_requires_ssid(self, api_client):
        r = api_client.post("/api/wifi/configure", json={"password": "pw"})
        assert r.status_code == 422   # missing required field


# ── Settings API ──────────────────────────────────────────────────────────────

class TestSettingsIntegration:
    def test_write_multiple_keys(self, api_client):
        from database import get_setting
        keys = {"vol": "75", "hotspot_active": "false", "active_user_id": "3"}
        for k, v in keys.items():
            api_client.put(f"/api/settings/{k}", json={"value": v})
        for k, v in keys.items():
            assert get_setting(k) == v

    def test_complete_setup_flag(self, api_client):
        from database import get_setting
        assert get_setting("setup_complete") == "false"
        api_client.post("/api/system/complete-setup")
        assert get_setting("setup_complete") == "true"


# ── Playback Integration ──────────────────────────────────────────────────────

class TestPlaybackIntegration:
    def test_volume_clamped_at_boundaries(self, api_client):
        for v, expected_status in [(0, 200), (100, 200), (101, 422), (-1, 422)]:
            r = api_client.post("/api/playback/volume", json={"volume": v})
            assert r.status_code == expected_status, f"volume={v} gave {r.status_code}"

    def test_all_buttons_respond(self, api_client):
        for btn in ("play_pause", "next", "prev", "vol_up", "vol_down"):
            r = api_client.post(f"/api/playback/button/{btn}")
            assert r.status_code == 200, f"button {btn} failed"

    def test_active_user_switches_volume(self, api_client):
        id1 = api_client.post("/api/users/", json={"name": "p", "display_name": "P", "volume": 30}).json()["id"]
        id2 = api_client.post("/api/users/", json={"name": "q", "display_name": "Q", "volume": 80}).json()["id"]
        api_client.post("/api/playback/active-user", json={"user_id": id1})
        s1 = api_client.get("/api/playback/state").json()["volume"]
        api_client.post("/api/playback/active-user", json={"user_id": id2})
        s2 = api_client.get("/api/playback/state").json()["volume"]
        assert s1 == 30
        assert s2 == 80

    def test_state_shape(self, api_client):
        d = api_client.get("/api/playback/state").json()
        for key in ("playing", "track", "artist", "album", "volume"):
            assert key in d


# ── Cross-cutting: RFID → User Login → Volume ────────────────────────────────

class TestEndToEndRfidUserFlow:
    def test_rfid_tag_resolves_to_user_and_sets_volume(self, tmp_db, api_client):
        """
        Simulates: child places RFID tag → system looks up tag → logs in user → sets volume.
        This exercises the full resolution path used in main._on_rfid_scan.
        """
        from database import get_engine, User, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session

        # Create child profile
        with Session(get_engine()) as s:
            user = User(name="child", display_name="Child", volume=55)
            s.add(user); s.commit(); s.refresh(user)
            child_id = user.id
            s.add(RfidTag(uid="KIDTAG1", tag_type="user", user_id=child_id, label="Child card"))
            s.commit()

        # Resolve tag
        with Session(get_engine()) as s:
            action = resolve_rfid_action(s, "KIDTAG1")
        assert action == {"type": "user_login", "user_id": child_id}

        # Activate via API (what _on_rfid_scan does)
        r = api_client.post("/api/playback/active-user", json={"user_id": child_id})
        assert r.json()["volume"] == 55

    def test_playlist_tag_resolves_correctly(self, tmp_db, api_client):
        from database import get_engine, RfidTag
        from models.user import resolve_rfid_action
        from sqlmodel import Session

        uri = "spotify:playlist:37i9dQZF1DXcBWIGoYBM5M"
        with Session(get_engine()) as s:
            s.add(RfidTag(uid="PLAY001", tag_type="playlist", spotify_uri=uri, label="Today's Hits"))
            s.commit()
            action = resolve_rfid_action(s, "PLAY001")

        assert action == {"type": "playlist", "spotify_uri": uri, "label": "Today's Hits"}

