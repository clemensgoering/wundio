import { useState } from "react";
import useSWR from "swr";
import { Card, Spinner } from "@/components/ui";

interface LogEvent {
  id:        number;
  level?:    string | null;
  source?:   string | null;
  message:   string;
  timestamp?: string | null;
}

const SOURCE_LABELS: Record<string, string> = {
  rfid:    "RFID",
  buttons: "Tasten",
  system:  "System",
  wifi:    "WLAN",
  spotify: "Musik",
  voice:   "Sprache",
};

const SOURCE_COLORS: Record<string, string> = {
  rfid:    "bg-honey/15 text-honey",
  buttons: "bg-sky-500/15 text-sky-400",
  system:  "bg-border text-muted",
  wifi:    "bg-teal/15 text-teal",
  spotify: "bg-green-500/15 text-green-400",
  voice:   "bg-purple-500/15 text-purple-400",
};

const LEVEL_DOT: Record<string, string> = {
  INFO:  "bg-teal",
  WARN:  "bg-amber",
  ERROR: "bg-red-500",
};

const SOURCES = ["", "rfid", "buttons", "system", "wifi", "spotify", "voice"];

function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    if (isNaN(d.getTime())) return "—";
    const date = d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit" });
    const time = d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
    return `${date} · ${time}`;
  } catch {
    return "—";
  }
}

export default function LogPage() {
  const [source, setSource] = useState("");
  const [limit,  setLimit]  = useState(100);

  const url = `/api/system/events?limit=${limit}${source ? `&source=${source}` : ""}`;

  const { data, error, isLoading, mutate } = useSWR<LogEvent[]>(
    url,
    async (u: string) => {
      const r = await fetch(u);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const json = await r.json();
      if (!Array.isArray(json)) throw new Error("Unexpected response");
      return json;
    },
    { refreshInterval: 5000, shouldRetryOnError: true }
  );

  const events = Array.isArray(data) ? data : [];

  return (
    <div className="max-w-3xl space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Aktivitäten</h1>
          <p className="text-muted text-sm">Alle Ereignisse – automatisch aktualisiert.</p>
        </div>
        <button
          onClick={() => mutate()}
          className="text-xs text-muted hover:text-paper border border-border
                     rounded-xl px-3 py-2 transition-colors"
        >
          Aktualisieren
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2">
        {SOURCES.map(s => (
          <button
            key={s}
            onClick={() => setSource(s)}
            className={`px-3 py-1.5 rounded-xl text-xs font-display font-bold
                        transition-colors border
                        ${source === s
                          ? "bg-honey text-white border-honey"
                          : "bg-surface border-border text-muted hover:text-paper"}`}
          >
            {s === "" ? "Alle" : (SOURCE_LABELS[s] ?? s)}
          </button>
        ))}
      </div>

      {/* Error state */}
      {error && (
        <Card className="p-6 text-center">
          <p className="text-muted text-sm mb-2">Aktivitäten konnten nicht geladen werden.</p>
          <p className="text-xs font-mono text-muted/50">{error.message}</p>
        </Card>
      )}

      {/* Loading */}
      {isLoading && !data && (
        <div className="flex justify-center py-16"><Spinner size={32} /></div>
      )}

      {/* Empty */}
      {!isLoading && !error && events.length === 0 && (
        <Card className="p-10 text-center">
          <p className="text-muted text-sm">Noch keine Aktivitäten vorhanden.</p>
        </Card>
      )}

      {/* Events */}
      {events.length > 0 && (
        <div className="space-y-1.5">
          {events.map(e => {
            const level  = e.level  ?? "INFO";
            const source = e.source ?? "system";
            return (
              <div key={e.id}
                   className="flex items-start gap-3 px-4 py-3 rounded-2xl
                              bg-surface border border-border/50
                              hover:border-border transition-colors">
                <div className="mt-1.5 flex-shrink-0">
                  <div className={`w-2 h-2 rounded-full ${LEVEL_DOT[level] ?? "bg-muted"}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-paper/85 leading-snug">{e.message}</p>
                </div>
                <div className="flex flex-col items-end gap-1 flex-shrink-0">
                  <span className={`text-[10px] font-display font-bold px-2 py-0.5 rounded-full
                                   ${SOURCE_COLORS[source] ?? "bg-border text-muted"}`}>
                    {SOURCE_LABELS[source] ?? source}
                  </span>
                  <span className="text-[10px] font-mono text-muted whitespace-nowrap">
                    {formatTime(e.timestamp)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Load more */}
      {events.length >= limit && (
        <div className="text-center">
          <button
            onClick={() => setLimit(l => l + 100)}
            className="text-xs text-muted hover:text-paper transition-colors"
          >
            Weitere laden...
          </button>
        </div>
      )}
    </div>
  );
}