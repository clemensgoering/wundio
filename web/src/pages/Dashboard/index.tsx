import useSWR from "swr";
import { api } from "@/lib/api";
import { Card, Badge, Spinner } from "@/components/ui";
import type { SystemStatus, PlaybackState } from "@/types/api";

export default function Dashboard() {
  const { data: status } = useSWR<SystemStatus>("status", () => api.status() as Promise<SystemStatus>, { refreshInterval: 5000 });
  const { data: playback } = useSWR<PlaybackState>("playback", () => api.playbackState() as Promise<PlaybackState>, { refreshInterval: 3000 });

  if (!status) return <div className="flex items-center justify-center h-full"><Spinner size={32} /></div>;

  const features = status.features;

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Dashboard</h1>
        <p className="text-muted text-sm">Systemübersicht und aktuelle Wiedergabe</p>
      </div>

      {/* Setup banner */}
      {!status.setup_complete && (
        <div className="border border-amber/30 bg-amber/5 rounded-2xl px-6 py-4 flex items-center gap-4">
          <span className="text-2xl">⚙️</span>
          <div>
            <p className="font-display font-semibold text-amber text-sm">Setup noch nicht abgeschlossen</p>
            <p className="text-muted text-xs mt-0.5">Bitte Einstellungen aufrufen und Konfiguration abschließen.</p>
          </div>
        </div>
      )}

      {/* Now playing */}
      {playback && (
        <Card className="p-6">
          <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">Aktuell</p>
          <div className="flex items-center gap-5">
            <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl flex-shrink-0
                             ${playback.playing ? "bg-amber/15" : "bg-surface"}`}>
              {playback.playing ? "🎵" : "⏸"}
            </div>
            <div className="min-w-0">
              <p className="font-display font-semibold text-paper truncate">
                {playback.track || (playback.playing ? "Wird abgespielt…" : "Nichts läuft")}
              </p>
              <p className="text-sm text-muted truncate">{playback.artist || "—"}</p>
            </div>
            <div className="ml-auto flex items-center gap-2 flex-shrink-0">
              <span className="text-sm text-muted">🔊 {playback.volume}%</span>
              <Badge color={playback.playing ? "teal" : "muted"}>
                {playback.playing ? "SPIELT" : "GESTOPPT"}
              </Badge>
            </div>
          </div>
        </Card>
      )}

      {/* Hardware info */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <InfoTile label="Modell"    value={status.hardware.model.replace("Raspberry Pi ", "Pi ") || "—"} />
        <InfoTile label="RAM"       value={`${status.hardware.ram_mb} MB`} />
        <InfoTile label="Pi Gen"    value={status.hardware.pi_generation ? `Gen ${status.hardware.pi_generation}` : "?"} />
      </div>

      {/* Feature flags */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">Features</p>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {Object.entries(features).map(([key, enabled]) => (
            <div key={key} className="flex items-center gap-2.5">
              <span className={`w-2 h-2 rounded-full ${enabled ? "bg-teal" : "bg-surface border border-border"}`} />
              <span className={`text-sm ${enabled ? "text-paper/70" : "text-muted/50"}`}>
                {key.replace(/_/g, " ")}
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function InfoTile({ label, value }: { label: string; value: string }) {
  return (
    <Card className="p-4">
      <p className="text-[10px] font-display font-semibold text-muted uppercase tracking-wider mb-1">{label}</p>
      <p className="font-display font-semibold text-paper text-sm truncate">{value}</p>
    </Card>
  );
}
