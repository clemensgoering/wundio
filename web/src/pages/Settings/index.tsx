import { useState, useEffect } from "react";
import useSWR from "swr";
import { Card, Input, Button, Badge, Spinner } from "@/components/ui";

interface EnvEntry {
  key:         string;
  label:       string;
  description: string;
  type:        string;
  section:     string;
  secret:      boolean;
  has_value:   boolean;
  value:       string;
  options?:    string[];
}

interface WifiStatus {
  configured: boolean;
  ssid:       string;
  hotspot:    boolean;
}

interface SystemStatus {
  local_ip: string;
}

const SECTION_LABELS: Record<string, string> = {
  spotify:     "Spotify – Gerät",
  spotify_api: "Spotify – Web API (für RFID Playlist-Autostart)",
  hotspot:     "WLAN Hotspot (Ersteinrichtung)",
  hardware:    "Hardware (Erweitert)",
};

const fetcher = async (url: string) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

function SpotifySetupGuide({ localIp, hasRefreshToken }: { localIp: string; hasRefreshToken: boolean }) {
  const redirectUri = `http://${localIp}:8000/api/spotify/callback`;
  const setupDocsUrl = `https://wundio.dev/docs/spotify-setup?box_ip=${localIp}`;

  if (hasRefreshToken) {
    return (
      <div className="bg-teal/10 border border-teal/30 rounded-2xl p-5 mb-4">
        <div className="flex items-start gap-3">
          <div className="w-6 h-6 rounded-full bg-teal flex-shrink-0 flex items-center justify-center mt-0.5">
            <span className="text-ink text-sm font-bold">✓</span>
          </div>
          <div>
            <p className="text-sm font-display font-semibold text-paper mb-1">
              Spotify ist verbunden
            </p>
            <p className="text-xs text-muted">
              Refresh Token ist gespeichert. Du kannst jetzt RFID-Tags Playlists zuweisen.
            </p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mb-4 space-y-4">
      {/* Quick Setup Guide */}
      <div className="bg-honey/10 border border-honey/30 rounded-2xl p-5">
        <p className="text-xs font-display font-bold text-paper mb-3 uppercase tracking-wider">
          Schnelleinrichtung (empfohlen)
        </p>
        <div className="space-y-3">
          <p className="text-sm text-muted">
            Öffne diese Seite auf deinem Handy oder Computer im selben Netzwerk:
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-ink/40 text-honey px-3 py-2 rounded-lg font-mono text-xs select-all">
              {setupDocsUrl}
            </code>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => navigator.clipboard.writeText(setupDocsUrl)}
            >
              Kopieren
            </Button>
          </div>
          <p className="text-xs text-muted/70">
            Die Seite führt dich Schritt-für-Schritt durch die Einrichtung und erzeugt einen QR-Code,
            den du mit deinem Handy scannen kannst.
          </p>
        </div>
      </div>

      {/* Manual Setup (Advanced) */}
      <details className="bg-ink/30 border border-border rounded-2xl">
        <summary className="px-5 py-3 cursor-pointer text-xs font-display font-semibold text-muted uppercase tracking-wider">
          Manuelle Einrichtung (Fortgeschritten)
        </summary>
        <div className="px-5 pb-5 space-y-4 pt-2">
          <div className="space-y-3">
            {/* Step 1 */}
            <div className="flex gap-3">
              <div className="w-6 h-6 rounded-full bg-border flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5">
                1
              </div>
              <div>
                <p className="text-sm font-display font-semibold text-paper mb-1">
                  Spotify Developer App anlegen
                </p>
                <p className="text-xs text-muted mb-2">
                  Gehe zu{" "}
                  <a
                    href="https://developer.spotify.com/dashboard"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-teal underline underline-offset-2"
                  >
                    developer.spotify.com/dashboard
                  </a>
                  {" "}→ "Create app"
                </p>
                <div className="bg-surface border border-border rounded-xl p-3 text-xs text-muted space-y-1.5">
                  <p>
                    <span className="text-paper font-semibold">App Name:</span> Wundio (beliebig)
                  </p>
                  <p>
                    <span className="text-paper font-semibold">Description:</span> Home music box (beliebig)
                  </p>
                  <p>
                    <span className="text-paper font-semibold">Redirect URI:</span>{" "}
                    <code className="bg-ink/40 text-honey px-1.5 py-0.5 rounded font-mono select-all">
                      {redirectUri}
                    </code>
                  </p>
                  <p className="text-muted/60 text-[10px]">
                    Wichtig: Diese exakte URI muss in der Spotify App eingetragen sein.
                  </p>
                </div>
              </div>
            </div>

            {/* Step 2 */}
            <div className="flex gap-3">
              <div className="w-6 h-6 rounded-full bg-border flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5">
                2
              </div>
              <div className="flex-1">
                <p className="text-sm font-display font-semibold text-paper mb-1">
                  Client ID & Secret hier eintragen
                </p>
                <p className="text-xs text-muted">
                  Zu finden im Spotify Dashboard unter "Settings" deiner App.
                  Weiter unten in den Feldern eintragen und speichern.
                </p>
              </div>
            </div>

            {/* Step 3 */}
            <div className="flex gap-3">
              <div className="w-6 h-6 rounded-full bg-border flex-shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5">
                3
              </div>
              <div className="flex-1">
                <p className="text-sm font-display font-semibold text-paper mb-2">
                  Mit Spotify autorisieren
                </p>
                <p className="text-xs text-muted mb-2">
                  Nach dem Speichern erscheint hier ein "Mit Spotify verbinden" Button.
                </p>
              </div>
            </div>
          </div>
        </div>
      </details>
    </div>
  );
}

export default function SettingsPage() {
  const { data: entries, mutate } = useSWR<EnvEntry[]>("/api/settings/env/all", fetcher);
  const { data: wifi } = useSWR<WifiStatus>("/api/wifi/status", fetcher, { refreshInterval: 10000 });
  const { data: status } = useSWR<SystemStatus>("/api/system/status", fetcher);

  const [changed, setChanged] = useState<Record<string, string>>({});
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (entries) {
      const initial: Record<string, string> = {};
      entries.forEach(e => { initial[e.key] = e.value || ""; });
      setChanged(initial);
    }
  }, [entries]);

  const patch = (key: string, val: string) => setChanged(c => ({ ...c, [key]: val }));

  const save = async (key: string) => {
    setLoading(true);
    setError("");
    try {
      await fetch(`/api/settings/env/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: changed[key] }),
      });
      setSaved(s => ({ ...s, [key]: true }));
      setTimeout(() => setSaved(s => ({ ...s, [key]: false })), 2000);
      mutate();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (!entries || !wifi || !status) return <Spinner />;

  const grouped = entries.reduce((acc, e) => {
    if (!acc[e.section]) acc[e.section] = [];
    acc[e.section].push(e);
    return acc;
  }, {} as Record<string, EnvEntry[]>);

  const hasClientId = entries.find(e => e.key === "SPOTIFY_CLIENT_ID")?.has_value || saved["SPOTIFY_CLIENT_ID"];
  const hasSecret = entries.find(e => e.key === "SPOTIFY_CLIENT_SECRET")?.has_value || saved["SPOTIFY_CLIENT_SECRET"];
  const hasRefreshToken = entries.find(e => e.key === "SPOTIFY_REFRESH_TOKEN")?.has_value;
  const credentialsReady = hasClientId && hasSecret;

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Einstellungen</h1>
        <p className="text-muted text-sm">Spotify, Hardware und System konfigurieren</p>
      </div>

      {error && (
        <Card className="bg-red-500/10 border-red-500/30 p-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {/* WiFi Status */}
      <Card className="p-5">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display font-bold text-lg text-paper">WLAN Status</h2>
          <Badge color={wifi.configured ? "teal" : "amber"}>
            {wifi.configured ? "Verbunden" : "Nicht konfiguriert"}
          </Badge>
        </div>
        {wifi.configured ? (
          <p className="text-sm text-muted">
            Verbunden mit: <span className="text-paper font-semibold">{wifi.ssid}</span>
          </p>
        ) : (
          <p className="text-sm text-muted">
            Noch kein Netzwerk konfiguriert. Unter{" "}
            <span className="text-paper font-mono">WLAN Hotspot</span> kannst du ein Netzwerk einrichten.
          </p>
        )}
      </Card>

      {/* Settings Sections */}
      {Object.entries(grouped).map(([section, items]) => (
        <Card key={section} className="p-6">
          <h2 className="font-display font-bold text-lg text-paper mb-4">
            {SECTION_LABELS[section] || section}
          </h2>

          {/* Spotify Setup Guide (only in spotify_api section) */}
          {section === "spotify_api" && (
            <SpotifySetupGuide localIp={status.local_ip} hasRefreshToken={hasRefreshToken || false} />
          )}

          <div className="space-y-4">
            {items.map(entry => {
              const isDirty = changed[entry.key] !== (entry.value || "");
              const wasSaved = saved[entry.key];

              return (
                <div key={entry.key}>
                  <label className="block text-xs font-display font-semibold text-muted mb-1.5">
                    {entry.label}
                  </label>
                  <p className="text-xs text-muted/70 mb-2">{entry.description}</p>

                  <div className="flex gap-2">
                    {entry.type === "select" ? (
                      <select
                        className="flex-1 bg-surface border border-border rounded-xl px-3 py-2.5 text-sm text-paper"
                        value={changed[entry.key] || ""}
                        onChange={e => patch(entry.key, e.target.value)}
                      >
                        {entry.options?.map(opt => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        type={entry.secret ? "password" : "text"}
                        placeholder={entry.has_value ? "●●●●●●●●" : "Nicht gesetzt"}
                        value={changed[entry.key] || ""}
                        onChange={e => patch(entry.key, e.target.value)}
                        className="flex-1"
                      />
                    )}

                    <Button
                      variant={wasSaved ? "success" : isDirty ? "primary" : "secondary"}
                      size="sm"
                      onClick={() => save(entry.key)}
                      disabled={!isDirty || loading}
                    >
                      {wasSaved ? "✓ Gespeichert" : isDirty ? "Speichern" : "OK"}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>

          {/* OAuth Button (only in spotify_api section, after credentials are saved) */}
          {section === "spotify_api" && credentialsReady && !hasRefreshToken && (
            <div className="mt-6 pt-6 border-t border-border">
              <a href="/api/spotify/auth/start">
                <Button variant="primary" className="w-full">
                  Mit Spotify verbinden
                </Button>
              </a>
              <p className="text-xs text-muted text-center mt-2">
                Du wirst zu Spotify weitergeleitet und musst die Verbindung autorisieren.
              </p>
            </div>
          )}
        </Card>
      ))}

      {/* System Actions */}
      <Card className="p-6">
        <h2 className="font-display font-bold text-lg text-paper mb-4">System</h2>
        <div className="space-y-3">
          <Button
            variant="secondary"
            onClick={async () => {
              if (confirm("Wundio neu starten?")) {
                await fetch("/api/system/restart", { method: "POST" });
              }
            }}
          >
            Neustart
          </Button>
          <p className="text-xs text-muted">
            Neustart erforderlich nach Änderungen an Hardware-Einstellungen (Display, RFID, Audio).
          </p>
        </div>
      </Card>
    </div>
  );
}
