"""
Wundio – Spotify Service (librespot)
Manages the librespot subprocess and exposes playback control.
librespot runs as a separate process; we communicate via:
  - subprocess signals for start/stop
  - librespot's --onevent script hook for state changes
  - /tmp/wundio-player.json for current track state (written by event hook)
"""

import asyncio
import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

STATE_FILE = Path("/tmp/wundio-player.json")
LIBRESPOT_BIN = "/opt/wundio/bin/librespot"


class PlaybackState:
    def __init__(self):
        self.playing: bool = False
        self.track_name: str = ""
        self.artist_name: str = ""
        self.album_name: str = ""
        self.volume: int = 70          # 0-100
        self.position_ms: int = 0
        self.duration_ms: int = 0
        self.spotify_uri: str = ""

    def to_dict(self) -> dict:
        return {
            "playing":      self.playing,
            "track":        self.track_name,
            "artist":       self.artist_name,
            "album":        self.album_name,
            "volume":       self.volume,
            "position_ms":  self.position_ms,
            "duration_ms":  self.duration_ms,
            "uri":          self.spotify_uri,
        }


class SpotifyService:
    """
    Wraps librespot.
    librespot acts as a Spotify Connect endpoint – the user connects
    to "Wundio" from any Spotify app on the same network, or we can
    trigger playback via the Spotify Web API (Phase 2).
    """

    def __init__(self, device_name: str = "Wundio", bitrate: int = 160):
        self._device_name = device_name
        self._bitrate = bitrate
        self._process: Optional[asyncio.subprocess.Process] = None
        self._state = PlaybackState()
        self._available = False

    def setup(self) -> bool:
        if not Path(LIBRESPOT_BIN).exists():
            # Try system librespot
            result = subprocess.run(["which", "librespot"], capture_output=True)
            if result.returncode != 0:
                logger.warning("librespot binary not found – Spotify unavailable")
                self._available = False
                return False
        self._available = True
        logger.info("librespot found – Spotify service ready")
        return True

    async def start(self) -> None:
        if not self._available:
            logger.info("Spotify service in mock mode (no librespot)")
            return

        bin_path = LIBRESPOT_BIN if Path(LIBRESPOT_BIN).exists() else "librespot"
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
        """Log librespot stdout/stderr and restart on crash."""
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

    def refresh_state(self) -> PlaybackState:
        """Read state written by the librespot event hook."""
        try:
            if STATE_FILE.exists():
                data = json.loads(STATE_FILE.read_text())
                self._state.playing      = data.get("playing", False)
                self._state.track_name   = data.get("track", "")
                self._state.artist_name  = data.get("artist", "")
                self._state.album_name   = data.get("album", "")
                self._state.position_ms  = data.get("position_ms", 0)
                self._state.duration_ms  = data.get("duration_ms", 0)
                self._state.spotify_uri  = data.get("uri", "")
        except Exception as e:
            logger.warning(f"Could not read player state: {e}")
        return self._state

    def get_state(self) -> PlaybackState:
        return self._state

    def set_volume(self, volume: int) -> None:
        """0-100. Sends SIGUSR1 to librespot (custom patch) or uses amixer."""
        volume = max(0, min(100, volume))
        self._state.volume = volume
        # Map 0-100 → 0-65535 for amixer
        amixer_vol = int(volume / 100 * 65535)
        try:
            subprocess.run(
                ["amixer", "sset", "Master", f"{amixer_vol}"],
                capture_output=True
            )
        except FileNotFoundError:
            logger.debug("amixer not available – volume mock")
        # Persist
        STATE_FILE.parent.mkdir(exist_ok=True)
        try:
            state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
            state["volume"] = volume
            STATE_FILE.write_text(json.dumps(state))
        except Exception:
            pass

    def play_uri(self, spotify_uri: str) -> bool:
        """
        Trigger playback of a Spotify URI on this device via the Web API.
        Requires SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN
        to be set in wundio.env. Returns True if the request was sent.
        """
        try:
            from config import get_settings
            cfg = get_settings()
            client_id     = getattr(cfg, "spotify_client_id",     "")
            client_secret = getattr(cfg, "spotify_client_secret", "")
            refresh_token = getattr(cfg, "spotify_refresh_token", "")

            if not all([client_id, client_secret, refresh_token]):
                logger.info(
                    f"Spotify Web API not configured – cannot auto-play {spotify_uri}. "
                    "Add SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REFRESH_TOKEN "
                    "to /etc/wundio/wundio.env"
                )
                return False

            # Get fresh access token
            import urllib.request
            import urllib.parse
            import base64
            creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
            token_req = urllib.request.Request(
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
            import json as _json
            with urllib.request.urlopen(token_req, timeout=5) as resp:
                token_data = _json.loads(resp.read())
            access_token = token_data.get("access_token", "")
            if not access_token:
                logger.warning("Spotify token refresh failed")
                return False

            # Get device ID of this Wundio instance
            devices_req = urllib.request.Request(
                "https://api.spotify.com/v1/me/player/devices",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            with urllib.request.urlopen(devices_req, timeout=5) as resp:
                devices = _json.loads(resp.read()).get("devices", [])

            device_id = None
            for d in devices:
                if self._device_name.lower() in d.get("name", "").lower():
                    device_id = d["id"]
                    break
            if not device_id and devices:
                device_id = devices[0]["id"]  # fallback to first device
            if not device_id:
                logger.warning("No Spotify device found – is librespot running?")
                return False

            # Start playback
            play_body = _json.dumps({
                "context_uri": spotify_uri if "playlist" in spotify_uri or "album" in spotify_uri else None,
                "uris":        [spotify_uri] if "track" in spotify_uri else None,
            }).encode()
            # Remove None values
            play_data = {k: v for k, v in _json.loads(play_body).items() if v is not None}
            play_req = urllib.request.Request(
                f"https://api.spotify.com/v1/me/player/play?device_id={device_id}",
                data=_json.dumps(play_data).encode(),
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type":  "application/json",
                },
                method="PUT",
            )
            with urllib.request.urlopen(play_req, timeout=5) as resp:
                logger.info(f"Spotify playback started: {spotify_uri} (status {resp.status})")
            return True

        except Exception as e:
            logger.warning(f"Spotify play_uri failed: {e}")
            return False

    def stop(self) -> None:
        if self._process:
            self._process.terminate()
            self._process = None


_service: Optional[SpotifyService] = None


def get_spotify_service() -> SpotifyService:
    global _service
    if _service is None:
        _service = SpotifyService()
    return _service