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
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

from config import get_settings

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
        self.volume: int      = 70      # 0-100
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

    def __init__(self, device_name: str = "Wundio", bitrate: int = 160) -> None:
        self._device_name = device_name
        self._bitrate     = bitrate
        self._process: Optional[asyncio.subprocess.Process] = None
        self._state       = PlaybackState()
        self._available   = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def setup(self) -> bool:
        """Locate the librespot binary. Returns True when found."""
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
        """Spawn the librespot subprocess. No-op when unavailable."""
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

        logger.info(f"Starting librespot: {' '.join(cmd)}")
        self._process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        asyncio.create_task(self._monitor())

    async def _monitor(self) -> None:
        """Log librespot stderr and restart automatically on unexpected exit."""
        if not self._process:
            return
        async for line in self._process.stderr:
            decoded = line.decode().strip()
            if decoded:
                logger.debug(f"[librespot] {decoded}")
        ret = await self._process.wait()
        if ret != 0:
            logger.warning(f"librespot exited with code {ret} – restarting in 5s")
            await asyncio.sleep(5)
            await self.start()

    def stop(self) -> None:
        """Terminate the librespot subprocess."""
        if self._process:
            self._process.terminate()
            self._process = None

    # ── State ─────────────────────────────────────────────────────────────────

    def refresh_state(self) -> PlaybackState:
        """Read the state file written by the librespot event hook."""
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
        except Exception as e:
            logger.warning(f"Could not read player state: {e}")
        return self._state

    def get_state(self) -> PlaybackState:
        """Return the last known playback state without reading the state file."""
        return self._state

    # ── Volume ────────────────────────────────────────────────────────────────

    def set_volume(self, volume: int) -> None:
        """Set playback volume (0-100).

        Uses `amixer sset Master <n>%` which works across all supported audio
        backends (USB soundcard, MAX98357A I2S DAC, HiFiBerry HAT).
        The raw 0-65535 scale used previously only worked on certain ALSA cards.
        """
        volume = max(0, min(100, volume))
        self._state.volume = volume
        try:
            subprocess.run(
                ["amixer", "sset", "Master", f"{volume}%"],
                capture_output=True,
            )
        except FileNotFoundError:
            logger.debug("amixer not available – volume mock")

        # Persist volume so it survives restarts
        STATE_FILE.parent.mkdir(exist_ok=True)
        try:
            state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
            state["volume"] = volume
            STATE_FILE.write_text(json.dumps(state))
        except Exception:
            pass

    # ── Playback control ──────────────────────────────────────────────────────

    def _fetch_access_token(self, client_id: str, client_secret: str, refresh_token: str) -> str:
        """Exchange a refresh token for a short-lived access token.

        Raises on network or auth errors so callers can handle them uniformly.
        Returns the access token string.
        """
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

    def _find_device_id(self, access_token: str) -> Optional[str]:
        """Return the device ID of this Wundio instance from the Spotify API.

        Prefers a device whose name matches self._device_name; falls back to
        the first available device. Returns None when no devices are active
        (librespot not running or not yet visible to Spotify).
        """
        req = urllib.request.Request(
            "https://api.spotify.com/v1/me/player/devices",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            devices = json.loads(resp.read()).get("devices", [])

        for d in devices:
            if self._device_name.lower() in d.get("name", "").lower():
                return d["id"]
        if devices:
            return devices[0]["id"]   # fallback to first active device
        return None

    def _send_play_request(self, access_token: str, device_id: str, spotify_uri: str) -> None:
        """Issue a PUT /me/player/play request to start the given URI.

        Raises on HTTP errors so the caller can log/handle them.
        """
        # Playlists and albums use context_uri; tracks use uris[]
        if "playlist" in spotify_uri or "album" in spotify_uri:
            body = {"context_uri": spotify_uri}
        else:
            body = {"uris": [spotify_uri]}

        req = urllib.request.Request(
            f"https://api.spotify.com/v1/me/player/play?device_id={device_id}",
            data=json.dumps(body).encode(),
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type":  "application/json",
            },
            method="PUT",
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(f"Spotify playback started: {spotify_uri} (HTTP {resp.status})")

    def _play_uri_sync(self, spotify_uri: str) -> bool:
        """Blocking implementation of play_uri – runs in a thread pool.

        Separated so that the async wrapper can use asyncio.to_thread without
        capturing `self` in a closure, and so unit tests can call it directly.
        """
        cfg           = get_settings()
        client_id     = cfg.spotify_client_id
        client_secret = cfg.spotify_client_secret
        refresh_token = cfg.spotify_refresh_token

        if not all([client_id, client_secret, refresh_token]):
            logger.info(
                f"Spotify Web API not configured – cannot auto-play {spotify_uri}. "
                "Add SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN "
                "to /etc/wundio/wundio.env"
            )
            return False

        try:
            access_token = self._fetch_access_token(client_id, client_secret, refresh_token)
        except Exception as e:
            logger.warning(f"Spotify token refresh failed: {e}")
            return False

        try:
            device_id = self._find_device_id(access_token)
        except Exception as e:
            logger.warning(f"Spotify device lookup failed: {e}")
            return False

        if not device_id:
            logger.warning("No Spotify device found – is librespot running?")
            return False

        try:
            self._send_play_request(access_token, device_id, spotify_uri)
        except Exception as e:
            logger.warning(f"Spotify play request failed: {e}")
            return False

        return True

    async def play_uri(self, spotify_uri: str) -> bool:
        """Trigger playback of a Spotify URI on this device (non-blocking).

        Requires SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET and
        SPOTIFY_REFRESH_TOKEN in /etc/wundio/wundio.env.

        Runs the three Spotify API calls (token refresh, device lookup, play)
        in a thread pool so the async event loop is never blocked – critical
        for meeting the ≤2 s RFID response requirement.

        Returns True if the play request was sent successfully.
        """
        return await asyncio.to_thread(self._play_uri_sync, spotify_uri)


# ── Singleton ──────────────────────────────────────────────────────────────────

_service: Optional[SpotifyService] = None


def get_spotify_service() -> SpotifyService:
    global _service
    if _service is None:
        _service = SpotifyService()
    return _service