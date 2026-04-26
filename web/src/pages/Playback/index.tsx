import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Card, Button, Spinner } from "@/components/ui";
import type { PlaybackState } from "@/types/api";

export default function PlaybackPage() {
  const { data: state, mutate } = useSWR<PlaybackState>(
    "playback",
    () => api.playbackState() as Promise<PlaybackState>,
    { refreshInterval: 2000 } // Poll every 2 seconds
  );

  const [loading, setLoading] = useState(false);

  const playPause = async () => {
    setLoading(true);
    try {
      await fetch("/api/playback/toggle", { method: "POST" });
      mutate();
    } finally {
      setLoading(false);
    }
  };

  const next = async () => {
    setLoading(true);
    try {
      await fetch("/api/playback/next", { method: "POST" });
      mutate();
    } finally {
      setLoading(false);
    }
  };

  const prev = async () => {
    setLoading(true);
    try {
      await fetch("/api/playback/prev", { method: "POST" });
      mutate();
    } finally {
      setLoading(false);
    }
  };

  const setVolume = async (vol: number) => {
    await fetch("/api/playback/volume", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ volume: vol }),
    });
    mutate();
  };

  if (!state) return <Spinner />;

  const progress = state.duration_ms > 0 ? (state.position_ms / state.duration_ms) * 100 : 0;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Wiedergabe</h1>
        <p className="text-muted text-sm">Aktuelle Musik-Wiedergabe steuern</p>
      </div>

      {/* Current Track */}
      <Card className="p-6">
        {state.track ? (
          <div>
            <div className="flex items-start gap-4 mb-4">
              {/* Album Art Placeholder */}
              <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-teal to-amber flex-shrink-0 flex items-center justify-center">
                <span className="text-3xl">🎵</span>
              </div>

              {/* Track Info */}
              <div className="flex-1 min-w-0">
                <h2 className="font-display font-bold text-xl text-paper mb-1 truncate">
                  {state.track}
                </h2>
                <p className="text-sm text-muted truncate">{state.artist}</p>
                {state.album && (
                  <p className="text-xs text-muted/70 truncate mt-0.5">{state.album}</p>
                )}
              </div>

              {/* Playing Indicator */}
              {state.playing && (
                <div className="flex-shrink-0 flex items-center gap-1">
                  <div className="w-1 h-3 bg-teal rounded-full animate-pulse" style={{ animationDelay: "0ms" }} />
                  <div className="w-1 h-4 bg-teal rounded-full animate-pulse" style={{ animationDelay: "150ms" }} />
                  <div className="w-1 h-3 bg-teal rounded-full animate-pulse" style={{ animationDelay: "300ms" }} />
                </div>
              )}
            </div>

            {/* Progress Bar */}
            <div className="mb-4">
              <div className="h-2 bg-surface rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-teal to-amber transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-muted mt-1">
                <span>{formatTime(state.position_ms)}</span>
                <span>{formatTime(state.duration_ms)}</span>
              </div>
            </div>

            {/* Controls */}
            <div className="flex items-center justify-center gap-3">
              <Button
                variant="secondary"
                size="sm"
                onClick={prev}
                disabled={loading}
                className="w-12 h-12 rounded-full"
              >
                ⏮
              </Button>
              <Button
                variant="primary"
                onClick={playPause}
                disabled={loading}
                className="w-14 h-14 rounded-full text-2xl"
              >
                {state.playing ? "⏸" : "▶️"}
              </Button>
              <Button
                variant="secondary"
                size="sm"
                onClick={next}
                disabled={loading}
                className="w-12 h-12 rounded-full"
              >
                ⏭
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-8">
            <p className="text-2xl mb-2">🎵</p>
            <p className="text-muted text-sm">
              Keine Wiedergabe aktiv
            </p>
            <p className="text-xs text-muted/70 mt-1">
              Lege einen RFID-Tag mit Playlist auf den Reader
            </p>
          </div>
        )}
      </Card>

      {/* Volume Control */}
      <Card className="p-6">
        <div className="flex items-center gap-4">
          <span className="text-muted text-sm font-display font-semibold w-24">
            Lautstärke
          </span>
          <input
            type="range"
            min="0"
            max="100"
            value={state.volume}
            onChange={(e) => setVolume(parseInt(e.target.value))}
            className="flex-1 h-2 bg-surface rounded-full appearance-none cursor-pointer
                       [&::-webkit-slider-thumb]:appearance-none
                       [&::-webkit-slider-thumb]:w-4
                       [&::-webkit-slider-thumb]:h-4
                       [&::-webkit-slider-thumb]:rounded-full
                       [&::-webkit-slider-thumb]:bg-amber
                       [&::-webkit-slider-thumb]:cursor-pointer"
          />
          <span className="text-paper font-mono text-sm w-12 text-right">
            {state.volume}%
          </span>
        </div>
      </Card>

      {/* Quick Actions */}
      <Card className="p-6">
        <p className="text-xs font-display font-bold text-muted uppercase tracking-wider mb-3">
          Schnellaktionen
        </p>
        <div className="grid grid-cols-2 gap-3">
          <Button variant="secondary" size="sm">
            🔀 Shuffle
          </Button>
          <Button variant="secondary" size="sm">
            🔁 Repeat
          </Button>
          <Button variant="secondary" size="sm">
            ⏱️ Sleep Timer
          </Button>
          <Button variant="secondary" size="sm">
            ⭐ Favoriten
          </Button>
        </div>
      </Card>

      {/* Spotify URI Info */}
      {state.uri && (
        <Card className="p-4 bg-surface/50">
          <p className="text-[10px] text-muted uppercase tracking-wider mb-1">Spotify URI</p>
          <code className="text-xs font-mono text-muted/70 select-all break-all">
            {state.uri}
          </code>
        </Card>
      )}
    </div>
  );
}

function formatTime(ms: number): string {
  const seconds = Math.floor(ms / 1000);
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}