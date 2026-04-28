import { useState, useRef, useEffect } from "react";
import useSWR from "swr";
import { Card, Button, Spinner } from "@/components/ui";
import ServicesStatus from "./ServicesStatus";

interface ActionInfo {
  key: string;
  label: string;
  destructive: boolean;
  estimated_seconds: number;
  available: boolean;
}

type RunState = "idle" | "confirm" | "running" | "done" | "error";

interface ActionState {
  runState: RunState;
  lines: string[];
  exitOk: boolean | null;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// Visual config per action key
const ACTION_META: Record<string, { icon: string; description: string; danger?: boolean }> = {
  "pull-quick": { icon: "⚡", description: "Zieht neuesten Code von GitHub (~30 Sek). Kein Frontend-Rebuild." },
  "pull-full": { icon: "🔄", description: "Code + React-Frontend neu bauen. Pi 3: ~15 Min, Pi 4: ~2 Min." },
  "system-update": { icon: "📦", description: "Aktualisiert OS-Pakete und Python-Bibliotheken." },
  "restart-service": { icon: "🔁", description: "Startet wundio-core neu – z.B. nach Konfigurationsänderungen." },
  "reboot": { icon: "🔌", description: "Fährt den Raspberry Pi neu hoch.", danger: true },
  "uninstall": { icon: "🗑️", description: "Entfernt Wundio vollständig vom System.", danger: true },
};

export default function SystemPage() {
  const { data: actions, isLoading } = useSWR<ActionInfo[]>("/api/system/actions", fetcher);
  const [states, setStates] = useState<Record<string, ActionState>>({});
  const logRefs = useRef<Record<string, HTMLDivElement | null>>({});

  // Auto-scroll log to bottom
  useEffect(() => {
    Object.keys(states).forEach((key) => {
      const el = logRefs.current[key];
      if (el) el.scrollTop = el.scrollHeight;
    });
  }, [states]);

  const getState = (key: string): ActionState =>
    states[key] ?? { runState: "idle", lines: [], exitOk: null };

  const setState = (key: string, patch: Partial<ActionState>) =>
    setStates((prev) => ({
      ...prev,
      [key]: { ...getState(key), ...patch },
    }));

  const handleClick = (action: ActionInfo) => {
    const s = getState(action.key);
    if (s.runState === "running") return;
    if (action.destructive && s.runState !== "confirm") {
      setState(action.key, { runState: "confirm", lines: [], exitOk: null });
      return;
    }
    runAction(action);
  };

  const runAction = async (action: ActionInfo) => {
    setState(action.key, { runState: "running", lines: [], exitOk: null });

    const url = `/api/system/actions/${action.key}/run${action.destructive ? "?confirm=true" : ""}`;
    try {
      const res = await fetch(url, { method: "POST" });
      if (!res.ok || !res.body) {
        const err = await res.json().catch(() => ({ detail: "Unbekannter Fehler" }));
        setState(action.key, {
          runState: "error",
          lines: [`Fehler: ${err.detail ?? res.statusText}`],
          exitOk: false,
        });
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const parts = buf.split("\n\n");
        buf = parts.pop() ?? "";

        for (const chunk of parts) {
          const eventMatch = chunk.match(/^event:\s*(.+)$/m);
          const dataMatch = chunk.match(/^data:\s*(.*)$/m);
          const event = eventMatch?.[1]?.trim();
          const data = dataMatch?.[1]?.replace(/\\n/g, "\n").trim() ?? "";

          if (event === "output" && data) {
            setStates((prev) => {
              const cur = prev[action.key] ?? { runState: "running", lines: [], exitOk: null };
              return { ...prev, [action.key]: { ...cur, lines: [...cur.lines, data] } };
            });
          } else if (event === "done") {
            setState(action.key, { runState: "done", exitOk: true });
          } else if (event === "error") {
            setState(action.key, {
              runState: "error",
              exitOk: false,
              ...(data ? { lines: [data] } : {}),
            });
          }
        }
      }
    } catch (err) {
      setState(action.key, {
        runState: "error",
        lines: [`Netzwerkfehler: ${err}`],
        exitOk: false,
      });
    }
  };

  if (isLoading) return <Spinner />;

  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">System</h1>
        <p className="text-muted text-sm">
          Updates, Neustart und Wartung – direkt aus dem Browser.
        </p>
      </div>
      
      {/* Service & Spotify device status */}
      <ServicesStatus />

      {/* Action groups */}
      <ActionGroup
        title="Updates"
        keys={["pull-quick", "pull-full", "system-update"]}
        actions={actions ?? []}
        states={states}
        logRefs={logRefs}
        onAction={handleClick}
        onCancel={(key) => setState(key, { runState: "idle" })}
        onReset={(key) => setState(key, { runState: "idle", lines: [], exitOk: null })}
      />

      <ActionGroup
        title="Dienst"
        keys={["restart-service"]}
        actions={actions ?? []}
        states={states}
        logRefs={logRefs}
        onAction={handleClick}
        onCancel={(key) => setState(key, { runState: "idle" })}
        onReset={(key) => setState(key, { runState: "idle", lines: [], exitOk: null })}
      />

      <ActionGroup
        title="Erweitert"
        keys={["reboot", "uninstall"]}
        actions={actions ?? []}
        states={states}
        logRefs={logRefs}
        onAction={handleClick}
        onCancel={(key) => setState(key, { runState: "idle" })}
        onReset={(key) => setState(key, { runState: "idle", lines: [], exitOk: null })}
      />
    </div>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────

function ActionGroup({
  title, keys, actions, states, logRefs, onAction, onCancel, onReset,
}: {
  title: string;
  keys: string[];
  actions: ActionInfo[];
  states: Record<string, ActionState>;
  logRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  onAction: (a: ActionInfo) => void;
  onCancel: (key: string) => void;
  onReset: (key: string) => void;
}) {
  const filtered = actions.filter((a) => keys.includes(a.key));
  if (!filtered.length) return null;

  return (
    <div>
      <h2 className="font-display font-bold text-xl text-paper mb-3">{title}</h2>
      <Card className="divide-y divide-border">
        {filtered.map((action) => (
          <ActionRow
            key={action.key}
            action={action}
            state={states[action.key] ?? { runState: "idle", lines: [], exitOk: null }}
            logRef={(el) => { logRefs.current[action.key] = el; }}
            onAction={() => onAction(action)}
            onCancel={() => onCancel(action.key)}
            onReset={() => onReset(action.key)}
          />
        ))}
      </Card>
    </div>
  );
}

function ActionRow({
  action, state, logRef, onAction, onCancel, onReset,
}: {
  action: ActionInfo;
  state: ActionState;
  logRef: (el: HTMLDivElement | null) => void;
  onAction: () => void;
  onCancel: () => void;
  onReset: () => void;
}) {
  const meta = ACTION_META[action.key] ?? { icon: "⚙️", description: "" };
  const { runState, lines } = state;
  const busy = runState === "running";

  const btnLabel = () => {
    if (busy) return "Läuft...";
    if (runState === "done") return "Erledigt ✓";
    if (runState === "error") return "Fehler – Wiederholen";
    if (runState === "confirm") return "Bestätigen & Ausführen";
    return action.label;
  };

  const btnColor = () => {
    if (meta.danger || action.destructive) {
      return runState === "confirm"
        ? "bg-red-600 hover:bg-red-700 text-white"
        : "bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30";
    }
    if (runState === "done") return "bg-teal/10 text-teal border border-teal/30";
    if (runState === "error") return "bg-honey/10 text-honey border border-honey/30";
    return "bg-teal text-ink hover:bg-teal/90";
  };

  const showLog = lines.length > 0 || busy;

  return (
    <div className="p-4 space-y-3">
      {/* Header row */}
      <div className="flex items-start gap-3">
        <span className="text-2xl mt-0.5 flex-shrink-0">{meta.icon}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-display font-semibold text-paper">{action.label}</p>
          <p className="text-xs text-muted mt-0.5">{meta.description}</p>
          {!action.available && (
            <p className="text-xs text-red-400 mt-1">Script nicht gefunden auf diesem System.</p>
          )}
        </div>
        <div className="flex gap-2 flex-shrink-0">
          {runState === "confirm" && (
            <button
              onClick={onCancel}
              className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted hover:text-paper"
            >
              Abbrechen
            </button>
          )}
          {(runState === "done" || runState === "error") && (
            <button
              onClick={onReset}
              className="px-3 py-1.5 text-xs rounded-lg border border-border text-muted hover:text-paper"
            >
              Zurücksetzen
            </button>
          )}
          <button
            onClick={onAction}
            disabled={busy || !action.available}
            className={`px-4 py-1.5 text-xs rounded-lg font-display font-semibold
                        transition-colors disabled:opacity-50 disabled:cursor-not-allowed
                        ${btnColor()}`}
          >
            {busy && (
              <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent
                               rounded-full animate-spin mr-2 align-middle" />
            )}
            {btnLabel()}
          </button>
        </div>
      </div>

      {/* Confirm warning */}
      {runState === "confirm" && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
          <p className="text-xs text-red-400 font-semibold">
            ⚠ Diese Aktion kann nicht rückgängig gemacht werden. Wirklich fortfahren?
          </p>
        </div>
      )}

      {/* Live log */}
      {showLog && (
        <div
          ref={logRef}
          className="bg-ink/60 border border-border/50 rounded-xl p-3 font-mono text-[11px]
                     text-paper/80 max-h-64 overflow-y-auto space-y-0.5 leading-relaxed"
        >
          {busy && lines.length === 0 && (
            <span className="text-muted animate-pulse">Warte auf Ausgabe...</span>
          )}
          {lines.map((line, i) => (
            <div key={i} className={lineColor(line)}>{line}</div>
          ))}
          {busy && (
            <div className="text-teal/60 animate-pulse mt-1">▌</div>
          )}
          {runState === "done" && (
            <div className="text-teal font-semibold mt-2">✓ Abgeschlossen</div>
          )}
          {runState === "error" && (
            <div className="text-red-400 font-semibold mt-2">✗ Fehler aufgetreten</div>
          )}
        </div>
      )}
    </div>
  );
}

function lineColor(line: string): string {
  const l = line.toLowerCase();
  if (l.includes("error") || l.includes("fehler") || l.includes("[error]")) return "text-red-400";
  if (l.includes("warn") || l.includes("[warn]")) return "text-honey";
  if (l.includes("[ ok ]") || l.includes("✓") || l.includes("ok")) return "text-teal";
  if (l.includes("===") || l.includes("───")) return "text-paper/40";
  return "text-paper/70";
}