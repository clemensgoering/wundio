#!/usr/bin/env bash
# Wundio - librespot event hook (librespot 0.8.0+)
#
# librespot 0.8.0 event names:
#   track_changed  - new track loaded, NAME and TRACK_ID are set
#   playing        - playback started (no NAME, only TRACK_ID)
#   paused         - playback paused
#   stopped        - playback stopped
#   end_of_track   - track finished

STATE_FILE="/tmp/wundio-player.json"

case "$PLAYER_EVENT" in
  track_changed)
    # Metadata available here. Keep current playing status.
    CURRENT_PLAYING="false"
    if [[ -f "$STATE_FILE" ]]; then
        CURRENT_PLAYING=$(grep -o '"playing":[[:space:]]*[a-z]*' "$STATE_FILE" | grep -o '[a-z]*$' || echo "false")
    fi
    printf '{"playing":%s,"track":"%s","artist":"%s","album":"%s","duration_ms":%s,"position_ms":%s,"uri":"spotify:track:%s"}\n' \
      "$CURRENT_PLAYING" \
      "${NAME:-}" \
      "${ARTISTS:-}" \
      "${ALBUM:-}" \
      "${DURATION_MS:-0}" \
      "${POSITION_MS:-0}" \
      "${TRACK_ID:-}" \
      > "$STATE_FILE"
    ;;

  playing)
    if [[ -f "$STATE_FILE" ]]; then
        sed -i 's/"playing":false/"playing":true/g' "$STATE_FILE"
    else
        printf '{"playing":true,"track":"","artist":"","album":"","duration_ms":0,"position_ms":0,"uri":"spotify:track:%s"}\n' \
          "${TRACK_ID:-}" > "$STATE_FILE"
    fi
    ;;

  paused|stopped|end_of_track)
    if [[ -f "$STATE_FILE" ]]; then
        sed -i 's/"playing":true/"playing":false/g' "$STATE_FILE"
    fi
    ;;

  *)
    exit 0
    ;;
esac