"""
Wundio – Spotify Service (go-librespot)

The box runs go-librespot as a child process with its own Spotify account
(recommended: a dedicated member of a Spotify Premium Family plan).

Login happens once via Spotify device authorization: go-librespot requests a
pairing code, Wundio shows it on the display and in the web UI, and a parent
enters it at spotify.com/pair. The credentials are persisted in
<config_dir>/state.json, so after every reboot the box logs in on its own –
no phone, no Spotify developer app, no Web API tokens.

All control (RFID playback, buttons, status) goes through go-librespot's local
HTTP API, bound to 127.0.0.1 only. Volume is set via `amixer` using standard
percentage syntax, which works across all supported audio backends (USB, I2S,
HiFiBerry); go-librespot's own volume stays at 100 %.
"""

import asyncio
import json
import logging
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

GO_LIBRESPOT_BIN = "/opt/wundio/bin/go-librespot"
RESTART_DELAY_S  = 5


class PlaybackState:
    """Snapshot of the current playback state."""

    def __init__(self) -> None:
        self.playing: bool    = False
        self.track_name: str  = ""
        self.artist_name: str = ""
        self.album_name: str  = ""
        self.volume: int      = 70
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.spotify_uri: str = ""
        self.context_uri: str = ""
        self.context_name: str = ""

    def to_dict(self) -> dict:
        return {
            "playing":     self.playing,
            "track":       self.track_name,
            "artist":      self.artist_name,
            "album":       self.album_name,
            "volume":      self.volume,
            "position_ms": self.position_ms,
            "duration_ms": self.duration_ms,
            "uri":         self.spotify_uri,
            "context_uri": self.context_uri,
            "context_name": self.context_name,
        }


class SpotifyService:
    """
    Wraps the go-librespot daemon and its local HTTP API.

    The daemon is a Spotify Connect endpoint (visible as "Wundio" in Spotify
    apps on the same network) and is logged in with the box's own account,
    so RFID tags can start playback at any time without a phone.
    """

    def __init__(self, bitrate: int = 160) -> None:
        from config import get_settings
        cfg = get_settings()
        self._bitrate      = getattr(cfg, "spotify_bitrate", 0) or bitrate
        self._device_name: str = getattr(cfg, "spotify_device_name", "") or "Wundio"
        self._config_dir   = Path(getattr(cfg, "spotify_config_dir", "") or "/var/lib/wundio/spotify")
        self._api_port: int = getattr(cfg, "spotify_api_port", 0) or 3678
        self._zeroconf: bool = bool(getattr(cfg, "spotify_zeroconf", True))
        self._bin_path     = GO_LIBRESPOT_BIN
        self._process: Optional[asyncio.subprocess.Process] = None
        self._stopping     = False
        self._state        = PlaybackState()
        self._available    = False
        logger.info("SpotifyService init – device_name='%s'", self._device_name)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def setup(self) -> bool:
        if Path(GO_LIBRESPOT_BIN).exists():
            self._bin_path  = GO_LIBRESPOT_BIN
            self._available = True
        else:
            found = shutil.which("go-librespot")
            self._available = found is not None
            if found:
                self._bin_path = found
        if not self._available:
            logger.warning("go-librespot binary not found – Spotify unavailable")
        else:
            logger.info("go-librespot found – Spotify service ready")
        return self._available

    def _build_config(self) -> dict:
        """go-librespot config. Written as JSON, which is valid YAML."""
        return {
            "device_name":      self._device_name,
            "device_type":      "speaker",
            "bitrate":          self._bitrate,
            "audio_backend":    "alsa",
            "audio_device":     "default",
            "volume_steps":     100,
            "initial_volume":   100,
            "zeroconf_enabled": self._zeroconf,
            "credentials":      {"type": "device_auth"},
            "server": {
                "enabled": True,
                "address": "127.0.0.1",
                "port":    self._api_port,
            },
        }

    def write_config(self) -> None:
        self._config_dir.mkdir(parents=True, exist_ok=True)
        (self._config_dir / "config.yml").write_text(
            json.dumps(self._build_config(), indent=2)
        )

    async def start(self) -> None:
        """Write the config and spawn go-librespot."""
        if not self._available:
            logger.info("Spotify service in mock mode (no go-librespot)")
            return

        self._stopping = False
        self.write_config()
        cmd = [self._bin_path, "-config_dir", str(self._config_dir)]
        logger.info("Starting go-librespot: %s", " ".join(cmd))
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        asyncio.create_task(self._monitor(self._process))

    async def _monitor(self, process: asyncio.subprocess.Process) -> None:
        """Forward go-librespot output to our log and restart on unexpected exit."""
        async for line in process.stdout:
            decoded = line.decode(errors="replace").strip()
            if decoded:
                logger.debug("[go-librespot] %s", decoded)
        ret = await process.wait()
        if self._stopping or process is not self._process:
            return
        logger.warning("go-librespot exited with code %d – restarting in %ds", ret, RESTART_DELAY_S)
        await asyncio.sleep(RESTART_DELAY_S)
        if not self._stopping:
            await self.start()

    def stop(self) -> None:
        """Terminate the daemon (app shutdown). Use pause() to stop playback."""
        self._stopping = True
        if self._process and self._process.returncode is None:
            self._process.terminate()
        self._process = None

    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None

    async def logout(self) -> bool:
        """
        Forget the box's Spotify account and restart go-librespot, which then
        requests a fresh pairing code.
        """
        self.stop()
        state_file = self._config_dir / "state.json"
        try:
            state_file.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Could not remove %s: %s", state_file, exc)
            return False
        await asyncio.sleep(1)
        await self.start()
        return True

    # ── Local API ─────────────────────────────────────────────────────────────

    def _api(self, method: str, path: str, body: dict | None = None,
             timeout: float = 5) -> tuple[int, Optional[dict]]:
        """
        Call go-librespot's local API. Returns (http_status, json_body).
        http_status is 0 when the daemon is not running or unreachable.
        """
        if not self.is_running():
            return 0, None
        data =json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self._api_port}{path}",
            data=data,
            headers={"Content-Type": "application/json"} if data else {},
            method=method,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                return resp.status, (json.loads(raw) if raw else None)
        except urllib.error.HTTPError as exc:
            logger.warning("go-librespot %s %s → HTTP %d", method, path, exc.code)
            return exc.code, None
        except Exception as exc:
            logger.debug("go-librespot %s %s unreachable: %s", method, path, exc)
            return 0, None

    def status_info(self) -> dict:
        """Login / pairing status for the web UI and the display."""
        info = {
            "installed":      self._available,
            "running":        self.is_running(),
            "logged_in":      False,
            "username":       "",
            "device_name":    self._device_name,
            "playback_ready": False,
            "pairing":        None,
        }
        if not info["running"]:
            return info

        code, root = self._api("GET", "/")
        if code == 200 and root:
            info["playback_ready"] = bool(root.get("playback_ready"))

        code, status = self._api("GET", "/status")
        if code == 200 and status:
            info["logged_in"]   = True
            info["username"]    = status.get("username") or ""
            info["device_name"] = status.get("device_name") or self._device_name
            return info

        code, pairing = self._api("GET", "/auth/code")
        if code == 200 and pairing:
            info["pairing"] = {
                "url":        pairing.get("url", ""),
                "code":       pairing.get("code", ""),
                "expires_at": pairing.get("expires_at", ""),
            }
        return info

    # ── State ─────────────────────────────────────────────────────────────────

    def refresh_state(self) -> PlaybackState:
        """Update the cached state from go-librespot. Keeps the last state on failure."""
        code, status = self._api("GET", "/status", timeout=2)
        if code == 204:
            self._state.playing = False
        elif code == 200 and status:
            track = status.get("track") or {}
            self._state.playing     = not (status.get("stopped") or status.get("paused"))
            self._state.track_name  = track.get("name", "")
            self._state.artist_name = ", ".join(track.get("artist_names") or [])
            self._state.album_name  = track.get("album_name", "")
            self._state.position_ms = track.get("position", 0)
            self._state.duration_ms = track.get("duration", 0)
            self._state.spotify_uri = track.get("uri", "")
            self._state.context_uri = status.get("context_uri") or ""
            self._state.context_name = status.get("context_name") or ""
        return self._state

    def get_state(self) -> PlaybackState:
        return self._state

    # ── Volume ────────────────────────────────────────────────────────────────

    def set_volume(self, volume: int) -> None:
        volume = max(0, min(100, volume))
        self._state.volume = volume
        try:
            subprocess.run(
                ["amixer", "sset", "Master", f"{volume}%"],
                capture_output=True,
            )
        except FileNotFoundError:
            logger.debug("amixer not available – volume mock")

    # ── Playback control ──────────────────────────────────────────────────────

    def play_uri(self, spotify_uri: str) -> bool:
        """
        Start playback of a Spotify URI (track, album, playlist, show, episode)
        on this box. Returns True if go-librespot accepted the request.
        """
        code, _ = self._api("POST", "/player/play", {"uri": spotify_uri}, timeout=10)
        if code == 200:
            logger.info("Playback started: %s", spotify_uri)
            return True
        logger.warning("Spotify play_uri failed for %s (HTTP %d)", spotify_uri, code)
        return False

    async def play_uri_async(self, spotify_uri: str) -> bool:
        """Non-blocking wrapper for play_uri – use from async contexts."""
        return await asyncio.to_thread(self.play_uri, spotify_uri)

    def _post(self, path: str) -> bool:
        code, _ = self._api("POST", path)
        return code == 200

    def pause(self) -> bool:
        return self._post("/player/pause")

    def resume(self) -> bool:
        return self._post("/player/resume")

    def next_track(self) -> bool:
        return self._post("/player/next")

    def prev_track(self) -> bool:
        return self._post("/player/prev")

    def toggle_play_pause(self) -> bool:
        ok = self._post("/player/playpause")
        if ok:
            self._state.playing = not self._state.playing
        return ok


# ── Singleton ─────────────────────────────────────────────────────────────────

_service: Optional[SpotifyService] = None


def get_spotify_service() -> SpotifyService:
    global _service
    if _service is None:
        _service = SpotifyService()
    return _service
