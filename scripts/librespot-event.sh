#!/usr/bin/env bash
# Wundio – librespot event hook
# Called by librespot for every player event.
# Env vars set by librespot:
#   PLAYER_EVENT  – e.g. "playing", "paused", "stopped", "changed"
#   TRACK_ID, NAME, ARTISTS, ALBUM, DURATION_MS, POSITION_MS

STATE_FILE="/tmp/wundio-player.json"

case "$PLAYER_EVENT" in
  playing|change)
    PLAYING="true"
    ;;
  paused|stopped|end_of_track)
    PLAYING="false"
    ;;
  *)
    exit 0
    ;;
esac

cat > "$STATE_FILE" << EOF
{
  "playing":     $PLAYING,
  "track":       "${NAME:-}",
  "artist":      "${ARTISTS:-}",
  "album":       "${ALBUM:-}",
  "duration_ms": ${DURATION_MS:-0},
  "position_ms": ${POSITION_MS:-0},
  "uri":         "spotify:track:${TRACK_ID:-}"
}
EOF
