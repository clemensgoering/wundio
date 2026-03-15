import { useState } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Button, Card, Spinner } from "@/components/ui";
import type { PlaybackState, User } from "@/types/api";

const BUTTONS = [
  { name: "prev",       icon: "⏮", label: "Zurück"    },
  { name: "play_pause", icon: "⏯", label: "Play/Pause" },
  { name: "next",       icon: "⏭", label: "Weiter"    },
] as const;

export default function Playback() {
  const { data: state, mutate } = useSWR<PlaybackState>(
    "playback", () => api.playbackState() as Promise<PlaybackState>, { refreshInterval: 2000 }
  );
  const { data: users } = useSWR<User[]>("users", () => api.listUsers() as Promise<User[]>);
  const [pressing, setPressing] = useState<string | null>(null);
  const [volDraft,  setVolDraft] = useState<number | null>(null);

  const press = async (name: string) => {
    setPressing(name);
    await api.pressButton(name).catch(() => {});
    await mutate();
    setPressing(null);
  };

  const commitVolume = async (v: number) => {
    await api.setVolume(v);
    setVolDraft(null);
    mutate();
  };

  const vol = volDraft ?? state?.volume ?? 70;

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Wiedergabe</h1>
        <p className="text-muted text-sm">Steuerung & Lautstärke</p>
      </div>

      {!state ? <Spinner /> : (
        <>
          {/* Now playing */}
          <Card className="p-8 text-center">
            <div className={`w-20 h-20 mx-auto rounded-3xl flex items-center justify-center text-5xl mb-5
                             ${state.playing ? "bg-amber/15" : "bg-surface"}`}>
              {state.playing ? "🎵" : "⏸"}
            </div>
            <p className="font-display font-bold text-xl text-paper mb-1">
              {state.track || "Nichts läuft"}
            </p>
            <p className="text-muted text-sm">{state.artist || "—"}</p>
            {state.album && <p className="text-muted/50 text-xs mt-1">{state.album}</p>}
          </Card>

          {/* Controls */}
          <Card className="p-6">
            <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-5">Steuerung</p>
            <div className="flex items-center justify-center gap-4">
              {BUTTONS.map(b => (
                <button key={b.name}
                  onClick={() => press(b.name)}
                  disabled={pressing !== null}
                  className={`flex flex-col items-center gap-1.5 px-5 py-3 rounded-2xl transition-all
                              ${pressing === b.name ? "bg-amber/20 scale-95" : "bg-surface hover:bg-amber/10 border border-border"}
                              disabled:opacity-50`}>
                  <span className="text-2xl">{b.icon}</span>
                  <span className="text-[10px] font-display text-muted">{b.label}</span>
                </button>
              ))}
            </div>

            {/* Volume slider */}
            <div className="mt-6 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-display font-medium text-muted">Lautstärke</span>
                <span className="text-sm font-display font-semibold text-amber">{vol}%</span>
              </div>
              <input
                type="range" min={0} max={100} value={vol}
                onChange={e => setVolDraft(+e.target.value)}
                onMouseUp={e => commitVolume(+(e.target as HTMLInputElement).value)}
                onTouchEnd={e => commitVolume(+(e.target as HTMLInputElement).value)}
                className="accent-amber w-full"
              />
              <div className="flex justify-between">
                <Button variant="ghost" size="sm" onClick={() => commitVolume(Math.max(0,  vol - 10))}>− 10</Button>
                <Button variant="ghost" size="sm" onClick={() => commitVolume(Math.min(100, vol + 10))}>+ 10</Button>
              </div>
            </div>
          </Card>

          {/* User switcher */}
          {users && users.length > 0 && (
            <Card className="p-6">
              <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">Aktives Kind</p>
              <div className="flex flex-wrap gap-2">
                {users.map(u => (
                  <button key={u.id}
                    onClick={() => api.setActiveUser(u.id).then(() => mutate())}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl border border-border bg-surface
                               hover:border-amber/30 hover:bg-amber/5 transition-all text-sm">
                    <span>{u.avatar_emoji}</span>
                    <span className="font-display font-medium text-paper/80">{u.display_name}</span>
                  </button>
                ))}
              </div>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
