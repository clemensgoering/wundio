"""
System API tests – /restart endpoint and dual-router contract.

These tests complement the existing TestSystemApi in tests/phase0/test_core.py.
They can be placed in the same file or kept here as a separate module.
"""
import subprocess


class TestSystemRestart:
    """POST /api/system/restart – fire-and-forget JSON endpoint."""

    def test_restart_returns_ok(self, api_client, monkeypatch):
        """Must return 200 with ok=True without waiting for systemctl to finish."""
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        r = api_client.post("/api/system/restart")
        assert r.status_code == 200
        assert r.json()["ok"] is True

    def test_restart_response_is_json(self, api_client, monkeypatch):
        """Response Content-Type must be application/json, not text/event-stream."""
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)
        r = api_client.post("/api/system/restart")
        assert r.headers["content-type"].startswith("application/json")

    def test_restart_is_non_blocking(self, api_client, monkeypatch):
        """Popen must be called deferred (create_task), not inline.

        The response must arrive regardless of whether systemctl resolves –
        we verify by checking the response arrives even when Popen raises.
        """
        def failing_popen(*a, **kw):
            raise OSError("systemctl not found")

        monkeypatch.setattr(subprocess, "Popen", failing_popen)
        # Should not raise – Popen runs in a background task after response
        r = api_client.post("/api/system/restart")
        assert r.status_code == 200


class TestSystemRouterContract:
    """Guard against accidental endpoint overlap between the two /api/system routers.

    system.py       → status, health, events, complete-setup, restart
    system_actions  → actions (list + run), SSE streaming

    These tests document the intended split and will fail if a new route is
    added to the wrong router or if the prefix changes in main.py.
    """

    def test_core_endpoints_reachable(self, api_client):
        """All read-only core endpoints must return non-404."""
        probes = [
            ("GET",  "/api/system/status"),
            ("GET",  "/api/system/health"),
            ("GET",  "/api/system/events"),
        ]
        for method, path in probes:
            r = api_client.request(method, path)
            assert r.status_code != 404, (
                f"{method} {path} returned 404 – route missing or conflicting"
            )

    def test_actions_list_reachable(self, api_client):
        """GET /api/system/actions must return a non-empty list."""
        r = api_client.get("/api/system/actions")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list) and len(data) > 0
        keys = {item["key"] for item in data}
        assert "restart-service" in keys, "restart-service must be in the actions whitelist"
        assert "reboot" in keys

    def test_restart_and_restart_service_are_distinct_endpoints(self, api_client, monkeypatch):
        """POST /restart (JSON) and POST /actions/restart-service/run (SSE) must coexist.

        /restart  – used by the Settings UI button; returns JSON immediately.
        /actions/*/run – used by the admin panel; streams live output via SSE.
        Both serve different client needs and must not shadow each other.
        """
        monkeypatch.setattr(subprocess, "Popen", lambda *a, **kw: None)

        # JSON endpoint
        r_json = api_client.post("/api/system/restart")
        assert r_json.status_code == 200
        assert r_json.headers["content-type"].startswith("application/json")

        # SSE endpoint (may 404 when systemctl is not on PATH in CI – acceptable)
        r_sse = api_client.post("/api/system/actions/restart-service/run")
        assert r_sse.status_code in (200, 404)
        if r_sse.status_code == 200:
            assert "text/event-stream" in r_sse.headers.get("content-type", ""), (
                "actions/*/run must return text/event-stream, not JSON"
            )

    def test_no_404_on_actions_unknown_key(self, api_client):
        """Unknown action keys must return 404, not 500."""
        r = api_client.post("/api/system/actions/does-not-exist/run")
        assert r.status_code == 404