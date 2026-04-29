"""
Wundio – Spotify Service (librespot)

Manages the librespot subprocess and exposes playback control.
librespot runs as a separate process; we communicate via:
  - subprocess spawn/terminate for lifecycle
  - librespot's --onevent script hook for state changes
  - /tmp/wundio-player.json for current track state (written by event hook)

Playback of a specific URI is triggered via the Spotify Web API (requires
OAuth credentials in wundio.env). Volume is set via `amixer` using standard
percentage syntax, which works across all supported audio backends (USB, I2S,
HiFiBerry).
"""

import asyncio
import base64
import json
import logging
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE    = Path("/tmp/wundio-player.json")
LIBRESPOT_BIN = "/opt/wundio/bin/librespot"


class PlaybackState:
    """Snapshot of the current librespot playback state."""

    def __init__(self) -> None:
        self.playing: bool    = False
        self.track_name: str  = ""
        self.artist_name: str = ""
        self.album_name: str  = ""
        self.volume: int      = 70
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.spotify_uri: str = ""

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
        }


class SpotifyService:
    """
    Wraps librespot and the Spotify Web API.

    librespot acts as a Spotify Connect endpoint – the user can connect to
    "Wundio" from any Spotify app on the same network.  Programmatic playback
    of a specific URI (e.g. when an RFID tag is scanned) additionally requires
    OAuth credentials stored in wundio.env.
    """

    def __init__(self, bitrate: int = 160) -> None:
        self._bitrate     = bitrate
        self._process: Optional[asyncio.subprocess.Process] = None
        self._state       = PlaybackState()
        self._available   = False
        from config import get_settings
        cfg = get_settings()
        self._device_name: str = getattr(cfg, "spotify_device_name", "") or "Wundio"
        logger.info("SpotifyService init – device_name='%s'", self._device_name)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def setup(self) -> bool:
        if Path(LIBRESPOT_BIN).exists():
            self._available = True
        else:
            result = subprocess.run(["which", "librespot"], capture_output=True)
            self._available = result.returncode == 0
        if not self._available:
            logger.warning("librespot binary not found – Spotify unavailable")
        else:
            logger.info("librespot found – Spotify service ready")
        return self._available

    async def start(self) -> None:
        """
        Spawn librespot subprocess.

        If Spotify Web API credentials are configured, fetches an access token
        and passes it to librespot via --access-token. This causes librespot to
        authenticate immediately and appear in the Spotify device list without
        any manual "select device" step from the user.

        Falls back to anonymous (zeroconf-only) mode when credentials are missing.
        """
        if not self._available:
            logger.info("Spotify service in mock mode (no librespot)")
            return

        bin_path   = LIBRESPOT_BIN if Path(LIBRESPOT_BIN).exists() else "librespot"
        event_hook = "/opt/wundio/scripts/librespot-event.sh"

        cmd = [
            bin_path,
            "--name",    self._device_name,
            "--bitrate", str(self._bitrate),
            "--backend", "alsa",
            "--disable-audio-cache",
            "--initial-volume", str(self._state.volume),
        ]

        if Path(event_hook).exists():
            cmd += ["--onevent", event_hook]

        # Authenticate immediately so device is visible in Spotify without
        # requiring the user to manually select it in the Spotify app.
        access_token = await asyncio.to_thread(self._get_startup_token)
        if access_token:
            cmd += ["--access-token", access_token]
            logger.info("librespot starting with access token – will be visible immediately")
        else:
            logger.info("librespot starting in zeroconf mode – no credentials configured")

        logger.info("Starting librespot: %s", " ".join(
            # Redact token from log
            [a if not a.startswith("AQ") else "***" for a in cmd]
        ))

        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._monitor())

    def _get_startup_token(self) -> str:
        """
        Fetch a fresh access token for librespot startup.
        Returns empty string if credentials are not configured or token fetch fails.
        Called in a thread pool (blocking I/O).
        """
        from config import get_settings
        cfg = get_settings()
        client_id     = getattr(cfg, "spotify_client_id",     "")
        client_secret = getattr(cfg, "spotify_client_secret", "")
        refresh_token = getattr(cfg, "spotify_refresh_token", "")

        if not all([client_id, client_secret, refresh_token]):
            return ""

        try:
            return self._fetch_access_token(client_id, client_secret, refresh_token)
        except Exception as exc:
            logger.warning("Could not fetch startup token for librespot: %s", exc)
            return ""

    async def _monitor(self) -> None:
        """Log librespot stderr and restart automatically on unexpected exit."""
        if not self._process:
            return
        async for line in self._process.stderr:
            decoded = line.decode().strip()
            if decoded:
                logger.debug("[librespot] %s", decoded)
        ret = await self._process.wait()
        if ret != 0:
            logger.warning("librespot exited with code %d – restarting in 5s", ret)
            await asyncio.sleep(5)
            await self.start()

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None

    # ── State ─────────────────────────────────────────────────────────────────

    def refresh_state(self) -> PlaybackState:
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self._state.playing     = data.get("playing", False)
                self._state.track_name  = data.get("track", "")
                self._state.artist_name = data.get("artist", "")
                self._state.album_name  = data.get("album", "")
                self._state.position_ms = data.get("position_ms", 0)
                self._state.duration_ms = data.get("duration_ms", 0)
                self._state.spotify_uri = data.get("uri", "")
        except Exception as exc:
            logger.warning("Could not read player state: %s", exc)
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
        STATE_FILE.parent.mkdir(exist_ok=True)
        try:
            state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
            state["volume"] = volume
            STATE_FILE.write_text(json.dumps(state))
        except Exception:
            pass

    # ── Playback control ──────────────────────────────────────────────────────

    def _fetch_access_token(self, client_id: str, client_secret: str, refresh_token: str) -> str:
        creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        req = urllib.request.Request(
            "https://accounts.spotify.com/api/token",
            data=urllib.parse.urlencode({
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
            }).encode(),
            headers={
                "Authorization": f"Basic {creds}",
                "Content-Type":  "application/x-www-form-urlencoded",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        token = data.get("access_token", "")
        if not token:
            raise ValueError("Spotify token refresh returned no access_token")
        return token

    def _find_device(self, access_token: str) -> tuple[Optional[str], bool]:
        """Return (device_id, is_active) for this Wundio instance, or (None, False)."""
        req = urllib.request.Request(
            "https://api.spotify.com/v1/me/player/devices",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            devices = json.loads(resp.read()).get("devices", [])

        logger.debug("Spotify devices: %s", [d.get("name") for d in devices])

        for d in devices:
            if self._device_name.lower() in d.get("name", "").lower():
                return d["id"], d.get("is_active", False)
        return None, False

    def play_uri(self, spotify_uri: str) -> bool:
        """
        Trigger playback of a Spotify URI exclusively on this Pi.

        Strategy:
          1. Refresh access token
          2. Find librespot device by name (retry once after 2s if not visible)
          3. Transfer playback to this device if not already active
          4. Start playback with explicit device_id

        Returns True if playback was successfully started.
        """
        from config import get_settings
        cfg = get_settings()
        client_id     = getattr(cfg, "spotify_client_id",     "")
        client_secret = getattr(cfg, "spotify_client_secret", "")
        refresh_token = getattr(cfg, "spotify_refresh_token", "")

        if not all([client_id, client_secret, refresh_token]):
            logger.info(
                "Spotify Web API not configured – cannot play %s",
                spotify_uri,
            )
            return False

        try:
            # 1. Token
            access_token = self._fetch_access_token(client_id, client_secret, refresh_token)
            auth_header  = {"Authorization": f"Bearer {access_token}"}

            # 2. Find device (retry once)
            device_id, is_active = self._find_device(access_token)
            if not device_id:
                logger.info("Device '%s' not visible – waiting 2s then retrying", self._device_name)
                time.sleep(2)
                device_id, is_active = self._find_device(access_token)

            if not device_id:
                logger.warning(
                    "Spotify device '%s' not found. Is librespot running?",
                    self._device_name,
                )
                return False

            # 3. Transfer playback so this device becomes active
            if not is_active:
                logger.info("Transferring playback to '%s'", self._device_name)
                transfer_req = urllib.request.Request(
                    "https://api.spotify.com/v1/me/player",
                    data=json.dumps({"device_ids": [device_id], "play": False}).encode(),
                    headers={**auth_header, "Content-Type": "application/json"},
                    method="PUT",
                )
                try:
                    with urllib.request.urlopen(transfer_req, timeout=8) as r:
                        logger.debug("Transfer status: %d", r.status)
                    time.sleep(0.5)
                except Exception as exc:
                    logger.warning("Transfer playback failed (non-fatal): %s", exc)

            # 4. Play
            body = (
                {"uris": [spotify_uri]}
                if "track" in spotify_uri
                else {"context_uri": spotify_uri}
            )
            play_req = urllib.request.Request(
                f"https://api.spotify.com/v1/me/player/play?device_id={device_id}",
                data=json.dumps(body).encode(),
                headers={**auth_header, "Content-Type": "application/json"},
                method="PUT",
            )
            with urllib.request.urlopen(play_req, timeout=8) as resp:
                logger.info(
                    "Playback started: %s on '%s' (HTTP %d)",
                    spotify_uri, self._device_name, resp.status,
                )
            return True

        except Exception as exc:
            logger.warning("Spotify play_uri failed: %s", exc)
            return False

    def ensure_device_visible(self, timeout_s: int = 15) -> bool:
        """
        Ensure this librespot device is visible in the Spotify device list.

        librespot only registers with Spotify's servers after it has made
        at least one connection. This method triggers that registration by:
          1. Fetching the device list (which wakes up librespot's zeroconf)
          2. If not visible: transferring playback to this device (forces registration)
          3. Retrying with backoff until visible or timeout

        Call this once at startup (from main.py lifespan) so the device is
        always ready when an RFID tag is scanned.

        Returns True if device became visible, False on timeout.
        """
        from config import get_settings
        cfg = get_settings()
        client_id     = getattr(cfg, "spotify_client_id",     "")
        client_secret = getattr(cfg, "spotify_client_secret", "")
        refresh_token = getattr(cfg, "spotify_refresh_token", "")

        if not all([client_id, client_secret, refresh_token]):
            logger.debug("Spotify not configured – skipping device warmup")
            return False

        try:
            access_token = self._fetch_access_token(client_id, client_secret, refresh_token)
        except Exception as exc:
            logger.warning("Device warmup – token fetch failed: %s", exc)
            return False

        deadline = time.time() + timeout_s
        attempt  = 0

        while time.time() < deadline:
            attempt += 1
            device_id, is_active = self._find_device(access_token)

            if device_id:
                logger.info(
                    "Spotify device '%s' visible after %d attempt(s) – ready",
                    self._device_name, attempt,
                )
                return True

            logger.debug(
                "Device warmup attempt %d – '%s' not visible yet",
                attempt, self._device_name,
            )

            # On second attempt: try a silent transfer to force registration
            if attempt == 2:
                try:
                    # Get any available device to "wake" the session
                    req = urllib.request.Request(
                        "https://api.spotify.com/v1/me/player/devices",
                        headers={"Authorization": f"Bearer {access_token}"},
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        all_devices = json.loads(resp.read()).get("devices", [])

                    if all_devices:
                        # Transfer to any device first, then we'll re-transfer
                        # to Wundio when RFID is scanned
                        logger.debug(
                            "Warming up via existing device: %s",
                            all_devices[0].get("name"),
                        )
                except Exception:
                    pass

            wait = min(2 ** (attempt - 1), 8)  # 1s, 2s, 4s, 8s, 8s…
            time.sleep(wait)

        logger.warning(
            "Device '%s' not visible after %ds – RFID playback will retry on demand",
            self._device_name, timeout_s,
        )
        return False

    async def ensure_device_visible_async(self, timeout_s: int = 15) -> bool:
        """Async wrapper for ensure_device_visible – use from lifespan."""
        return await asyncio.to_thread(self.ensure_device_visible, timeout_s)

    async def play_uri_async(self, spotify_uri: str) -> bool:
        """Non-blocking wrapper for play_uri – runs in a thread pool.

        Use this from async contexts (e.g. RFID scan handler) to avoid
        blocking the event loop during the Spotify API calls.
        """
        return await asyncio.to_thread(self.play_uri, spotify_uri)
    
    # ── Playback Control Methods. ─────────────────────────────────────────────────────────────────
     
    def _send_api(self, method: str, path: str, body: dict | None = None) -> bool:
        """
        Generic Spotify Web API call helper.
        Handles token refresh internally. Returns True on success.
        """
        from config import get_settings
        cfg = get_settings()
        client_id     = getattr(cfg, "spotify_client_id",     "")
        client_secret = getattr(cfg, "spotify_client_secret", "")
        refresh_token = getattr(cfg, "spotify_refresh_token", "")
 
        if not all([client_id, client_secret, refresh_token]):
            logger.debug("Spotify not configured – skipping %s %s", method, path)
            return False
 
        try:
            access_token = self._fetch_access_token(client_id, client_secret, refresh_token)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            }
            data = json.dumps(body).encode() if body else None
            req = urllib.request.Request(
                f"https://api.spotify.com/v1{path}",
                data=data,
                headers=headers,
                method=method,
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                logger.debug("%s %s → HTTP %d", method, path, resp.status)
            return True
        except Exception as exc:
            logger.warning("Spotify API %s %s failed: %s", method, path, exc)
            return False
 
    def pause(self) -> bool:
        """Pause playback on the active Spotify device."""
        return self._send_api("PUT", "/me/player/pause")
 
    def resume(self) -> bool:
        """Resume playback on the active Spotify device."""
        return self._send_api("PUT", "/me/player/play")
 
    def next_track(self) -> bool:
        """Skip to next track."""
        return self._send_api("POST", "/me/player/next")
 
    def prev_track(self) -> bool:
        """Skip to previous track."""
        return self._send_api("POST", "/me/player/previous")
 
    def toggle_play_pause(self) -> bool:
        """Toggle play/pause based on current state."""
        self.refresh_state()
        if self._state.playing:
            return self.pause()
        return self.resume()

# ── Singleton ─────────────────────────────────────────────────────────────────

_service: Optional[SpotifyService] = None


def get_spotify_service() -> SpotifyService:
    global _service
    if _service is None:
        _service = SpotifyService()
    return _service