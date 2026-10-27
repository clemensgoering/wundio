"""
Wundio – /api/spotify routes

The box logs in to Spotify once via device authorization: go-librespot
provides a pairing code, a parent enters it at spotify.com/pair, and the
credentials persist across reboots. No developer app, no OAuth relay.

Endpoints:
  GET  /api/spotify/status  – login state + pending pairing code
  POST /api/spotify/logout  – forget the box's account, request a new code
"""
import asyncio

from fastapi import APIRouter

from database import log_event
from services.spotify import get_spotify_service

router = APIRouter(tags=["spotify"])


@router.get("/status")
async def spotify_status():
    return await asyncio.to_thread(get_spotify_service().status_info)


@router.post("/logout")
async def spotify_logout():
    ok = await get_spotify_service().logout()
    if ok:
        log_event("spotify", "Spotify-Konto der Box abgemeldet – neuer Anmeldecode wird erzeugt")
    return {"ok": ok}
