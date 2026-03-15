# tests/conftest.py
"""
Shared fixtures and Pi hardware stubs.
Must be imported before any RPi/luma imports.
"""
import sys
import os
import unittest.mock as mock
import pytest

# ── Stub all Pi-only hardware modules ────────────────────────────────────────
_PI_STUBS = [
    "RPi", "RPi.GPIO", "spidev", "mfrc522",
    "luma", "luma.core", "luma.core.interface",
    "luma.core.interface.serial", "luma.core.render",
    "luma.oled", "luma.oled.device",
]
for mod in _PI_STUBS:
    sys.modules.setdefault(mod, mock.MagicMock())

# Make core importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../core"))


@pytest.fixture
def tmp_db(tmp_path):
    """Fresh isolated SQLite DB per test. Clears settings lru_cache so DB_PATH is re-read."""
    import database
    from config import get_settings
    database._engine = None
    get_settings.cache_clear()
    db_path = str(tmp_path / "wundio_test.db")
    os.environ["DB_PATH"] = db_path
    database.init_db(db_path)
    yield db_path
    database._engine = None
    get_settings.cache_clear()


@pytest.fixture
def api_client(tmp_db):
    """FastAPI TestClient with a fresh DB per test."""
    import database
    from fastapi.testclient import TestClient
    from main import app
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
