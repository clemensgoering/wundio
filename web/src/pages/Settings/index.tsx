import { useState } from "react";
import useSWR from "swr";
import { Card, Input, Button, Badge, Spinner } from "@/components/ui";
import InteractiveSpotifySetup from "./InteractiveSpotifySetup";

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

interface SpotifyStatus {
  has_client_id:     boolean;
  has_secret:        boolean;
  has_refresh_token: boolean;
  oauth_complete:    boolean;
}

const SECTION_LABELS: Record<string, string> = {
  spotify:  "Spotify – Gerät",
  hotspot:  "WLAN Hotspot (Ersteinrichtung)",
  hardware: "Hardware (Erweitert)",
};

// Sections rendered by custom components, not the generic field renderer
const CUSTOM_SECTIONS = new Set(["spotify_api"]);

const fetcher = async (url: string) => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

export default function SettingsPage() {
  const { data: entries, mutate } = useSWR<EnvEntry[]>("/api/settings/env/all", fetcher);
  const { data: wifi } = useSWR<WifiStatus>("/api/wifi/status", fetcher);
  const { data: spotifyStatus, mutate: mutateSpotify } = useSWR<SpotifyStatus>(
    "/api/settings/spotify/status",
    fetcher,
    { refreshInterval: 5000 } // poll every 5s so UI updates after OAuth callback
  );

  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [editing, setEditing] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});

  const save = async (key: string) => {
    const val = editing[key];
    if (val === undefined) return;
    setLoading({ ...loading, [key]: true });
    try {
      await fetch(`/api/settings/env/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: val }),
      });
      setSaved({ ...saved, [key]: true });
      mutate();
      mutateSpotify();
      setTimeout(() => setSaved({ ...saved, [key]: false }), 2000);
    } finally {
      setLoading({ ...loading, [key]: false });
    }
  };

  if (!entries || !Array.isArray(entries)) return <Spinner />;

  const bySection = entries.reduce((acc, e) => {
    if (!acc[e.section]) acc[e.section] = [];
    acc[e.section].push(e);
    return acc;
  }, {} as Record<string, EnvEntry[]>);

  return (
    <div className="max-w-4xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">
          Einstellungen
        </h1>
        <p className="text-muted text-sm">System-Konfiguration und Hardware-Einstellungen</p>
      </div>

      {/* WiFi Status */}
      {wifi && (
        <Card className="p-4 flex items-center gap-3">
          <div className="flex-shrink-0">
            {wifi.hotspot ? (
              <div className="w-10 h-10 rounded-full bg-honey/20 flex items-center justify-center">
                <span className="text-xl">📡</span>
              </div>
            ) : wifi.configured ? (
              <div className="w-10 h-10 rounded-full bg-teal/20 flex items-center justify-center">
                <span className="text-xl">✓</span>
              </div>
            ) : (
              <div className="w-10 h-10 rounded-full bg-red-500/20 flex items-center justify-center">
                <span className="text-xl">⚠</span>
              </div>
            )}
          </div>
          <div className="flex-1">
            <p className="text-sm font-display font-semibold text-paper">
              WLAN: {wifi.hotspot ? "Hotspot aktiv" : wifi.ssid || "Nicht verbunden"}
            </p>
            <p className="text-xs text-muted">
              {wifi.hotspot
                ? "Verbinde dich mit dem Hotspot um WLAN zu konfigurieren"
                : wifi.configured
                ? "Verbunden und bereit"
                : "Kein WLAN konfiguriert"}
            </p>
          </div>
        </Card>
      )}

      {/* Spotify Web API Setup – custom interactive component */}
      <div>
        <h2 className="font-display font-bold text-xl text-paper mb-3">
          Spotify Web API Setup
        </h2>
        <InteractiveSpotifySetup
          hasClientId={spotifyStatus?.has_client_id ?? false}
          hasSecret={spotifyStatus?.has_secret ?? false}
          hasRefreshToken={spotifyStatus?.has_refresh_token ?? false}
          onCredentialsSaved={mutateSpotify}
        />
      </div>

      {/* Generic Settings Sections (excludes custom-rendered ones) */}
      {Object.entries(bySection)
        .filter(([section]) => !CUSTOM_SECTIONS.has(section))
        .map(([section, items]) => (
          <div key={section}>
            <h2 className="font-display font-bold text-xl text-paper mb-3">
              {SECTION_LABELS[section] || section}
            </h2>

            <Card className="divide-y divide-border">
              {items.map((entry) => (
                <div key={entry.key} className="p-4">
                  <div className="flex items-start gap-3 mb-2">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <p className="text-sm font-display font-semibold text-paper">
                          {entry.label}
                        </p>
                        {entry.has_value && (
                          <Badge color="teal">Gesetzt</Badge>
                        )}
                        {saved[entry.key] && (
                          <Badge color="teal">✓ Gespeichert</Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted">{entry.description}</p>
                    </div>
                  </div>

                  <div className="flex gap-2">
                    {entry.type === "select" && entry.options ? (
                      <select
                        value={editing[entry.key] ?? entry.value ?? ""}
                        onChange={(e) =>
                          setEditing({ ...editing, [entry.key]: e.target.value })
                        }
                        className="flex-1 px-3 py-2 bg-surface border border-border rounded-lg
                                   text-sm text-paper focus:outline-none focus:ring-2 focus:ring-teal/50"
                      >
                        {entry.options.map((opt) => (
                          <option key={opt} value={opt}>{opt}</option>
                        ))}
                      </select>
                    ) : (
                      <Input
                        type={entry.type === "password" ? "password" : "text"}
                        placeholder={entry.has_value ? "••••••••" : "Wert eingeben..."}
                        value={editing[entry.key] ?? ""}
                        onChange={(e) =>
                          setEditing({ ...editing, [entry.key]: e.target.value })
                        }
                        className="flex-1 font-mono text-sm"
                      />
                    )}
                    <Button
                      onClick={() => save(entry.key)}
                      loading={loading[entry.key]}
                      disabled={editing[entry.key] === undefined}
                    >
                      Speichern
                    </Button>
                  </div>
                </div>
              ))}
            </Card>
          </div>
        ))}
    </div>
  );
}