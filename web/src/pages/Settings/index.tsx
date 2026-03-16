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

function SpotifySetupGuide({ entries, saved }: { entries: EnvEntry[]; saved: Record<string, boolean> }) {
  const hasClientId     = entries.find(e => e.key === "SPOTIFY_CLIENT_ID")?.has_value;
  const hasSecret       = entries.find(e => e.key === "SPOTIFY_CLIENT_SECRET")?.has_value;
  const hasRefreshToken = entries.find(e => e.key === "SPOTIFY_REFRESH_TOKEN")?.has_value;
  // Check if credentials were just saved in this session
  const justSavedId     = saved["SPOTIFY_CLIENT_ID"];
  const justSavedSecret = saved["SPOTIFY_CLIENT_SECRET"];

  const credentialsReady = (hasClientId || justSavedId) && (hasSecret || justSavedSecret);
  const redirectUri      = `${window.location.protocol}//${window.location.hostname}:${window.location.port || 8000}/api/spotify/callback`;

  return (
    <div className="mb-4 space-y-4">
      {/* Step guide */}
      <div className="bg-ink/30 border border-border rounded-2xl p-5">
        <p className="text-xs font-display font-bold text-paper mb-4 uppercase tracking-wider">
          Schritt-fuer-Schritt Einrichtung
        </p>
        <div className="space-y-4">

          {/* Step 1 */}
          <div className="flex gap-3">
            <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                            text-[10px] font-bold mt-0.5
                            ${hasClientId && hasSecret ? "bg-teal text-ink" : "bg-honey text-white"}`}>
              1
            </div>
            <div>
              <p className="text-sm font-display font-semibold text-paper mb-1">
                Spotify Developer App anlegen
              </p>
              <p className="text-xs text-muted mb-2">
                Gehe zu{" "}
                <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noopener noreferrer"
                   className="text-teal underline underline-offset-2">
                  developer.spotify.com/dashboard
                </a>
                {" "}&rarr; "Create app"
              </p>
              <div className="bg-surface border border-border rounded-xl p-3 text-xs text-muted space-y-1.5">
                <p><span className="text-paper font-semibold">App Name:</span> Wundio (beliebig)</p>
                <p><span className="text-paper font-semibold">Description:</span> Home music box (beliebig)</p>
                <p><span className="text-paper font-semibold">Redirect URI:</span>{" "}
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
            <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                            text-[10px] font-bold mt-0.5
                            ${hasClientId && hasSecret ? "bg-teal text-ink" : "bg-border text-muted"}`}>
              2
            </div>
            <div className="flex-1">
              <p className="text-sm font-display font-semibold text-paper mb-1">
                Client ID & Secret hier eintragen
              </p>
              <p className="text-xs text-muted">
                Zu finden im Spotify Dashboard unter "Settings" deiner App.
                Oben in den Feldern eintragen und speichern.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="flex gap-3">
            <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                            text-[10px] font-bold mt-0.5
                            ${hasRefreshToken ? "bg-teal text-ink" : "bg-border text-muted"}`}>
              3
            </div>
            <div className="flex-1">
              <p className="text-sm font-display font-semibold text-paper mb-2">
                Mit Spotify autorisieren
              </p>
              {hasRefreshToken ? (
                <div className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-teal flex-shrink-0" />
                  <p className="text-xs text-teal">Verbunden – Refresh Token gespeichert</p>
                </div>
              ) : credentialsReady ? (
                <a href="/api/spotify/auth/start"
                   className="inline-block px-4 py-2 bg-teal text-ink rounded-xl
                              text-xs font-display font-bold hover:bg-teal/90 transition-colors">
                  Mit Spotify verbinden
                </a>
              ) : (
                <p className="text-xs text-muted/60">
                  Zuerst Schritt 1 und 2 abschliessen.
                </p>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Reconnect option */}
      {hasRefreshToken && (
        <div className="flex items-center justify-between text-xs text-muted">
          <span>Anderen Spotify-Account verwenden?</span>
          <a href="/api/spotify/auth/start"
             className="text-teal underline underline-offset-2 hover:text-teal/70">
            Erneut autorisieren
          </a>
        </div>
      )}
    </div>
  );
}

export default function Settings() {
  const { data: envEntries, mutate: mutateEnv } =
    useSWR<EnvEntry[]>("/api/settings/env/all", fetcher);
  const { data: wifiStatus } =
    useSWR<WifiStatus>("/api/wifi/status", fetcher, { refreshInterval: 15000 });

  const [values,  setValues]  = useState<Record<string, string>>({});
  const [dirty,   setDirty]   = useState<Record<string, boolean>>({});
  const [saving,  setSaving]  = useState<Record<string, boolean>>({});
  const [saved,   setSaved]   = useState<Record<string, boolean>>({});
  const [errors,  setErrors]  = useState<Record<string, string>>({});
  const [showWifi, setShowWifi] = useState(false);
  const [wifiForm, setWifiForm] = useState({ ssid: "", password: "" });
  const [wifiSaving, setWifiSaving] = useState(false);
  const [restartBanner, setRestartBanner] = useState(false);

  // Init form values from env (skip masked secrets that already have a value)
  useEffect(() => {
    if (!envEntries) return;
    const init: Record<string, string> = {};
    envEntries.forEach(e => {
      init[e.key] = e.has_value && e.secret ? "" : e.value;
    });
    setValues(init);
  }, [envEntries]);

  const patch = (key: string, val: string) => {
    setValues(v => ({ ...v, [key]: val }));
    setDirty(d => ({ ...d, [key]: true }));
  };

  const save = async (key: string) => {
    const val = values[key] ?? "";
    setSaving(s => ({ ...s, [key]: true }));
    setErrors(e => ({ ...e, [key]: "" }));
    try {
      const r = await fetch(`/api/settings/env/${key}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: val }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.detail ?? "Fehler");
      setDirty(d => ({ ...d, [key]: false }));
      setSaved(s => ({ ...s, [key]: true }));
      if (data.restart_required) setRestartBanner(true);
      setTimeout(() => setSaved(s => ({ ...s, [key]: false })), 2500);
      mutateEnv();
    } catch (e: any) {
      setErrors(er => ({ ...er, [key]: e.message }));
    } finally {
      setSaving(s => ({ ...s, [key]: false }));
    }
  };

  const saveWifi = async () => {
    if (!wifiForm.ssid) return;
    setWifiSaving(true);
    try {
      await fetch("/api/wifi/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(wifiForm),
      });
      setShowWifi(false);
      setWifiForm({ ssid: "", password: "" });
    } finally { setWifiSaving(false); }
  };

  const restartService = async () => {
    await fetch("/api/system/restart", { method: "POST" }).catch(() => {});
    setRestartBanner(false);
  };

  if (!envEntries || !Array.isArray(envEntries)) return <div className="flex justify-center py-20"><Spinner size={32} /></div>;

  // Group by section
  const sections = Object.entries(
    envEntries.reduce((acc, e) => {
      (acc[e.section] = acc[e.section] ?? []).push(e);
      return acc;
    }, {} as Record<string, EnvEntry[]>)
  );

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Einstellungen</h1>
        <p className="text-muted text-sm">Konfiguration wird direkt in wundio.env gespeichert.</p>
      </div>

      {/* Restart banner */}
      {restartBanner && (
        <div className="bg-amber/10 border border-amber/30 rounded-2xl px-5 py-4 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-display font-bold text-amber">Neustart erforderlich</p>
            <p className="text-xs text-muted mt-0.5">
              Einige Änderungen werden erst nach dem Neustart des Dienstes aktiv.
            </p>
          </div>
          <Button size="sm" onClick={restartService}>Jetzt neu starten</Button>
        </div>
      )}

      {/* WiFi section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-1">
              WLAN
            </p>
            {wifiStatus?.configured && wifiStatus.ssid && (
              <p className="text-sm font-display font-bold text-paper">{wifiStatus.ssid}</p>
            )}
          </div>
          <Badge color={wifiStatus?.configured ? "teal" : "amber"}>
            {wifiStatus?.configured ? "Verbunden" : "Nicht verbunden"}
          </Badge>
        </div>

        {!showWifi ? (
          <Button variant="secondary" size="sm" onClick={() => setShowWifi(true)}>
            {wifiStatus?.configured ? "Netzwerk wechseln" : "WLAN einrichten"}
          </Button>
        ) : (
          <div className="space-y-3">
            <Input label="SSID" placeholder="Netzwerkname"
              value={wifiForm.ssid}
              onChange={e => setWifiForm(f => ({ ...f, ssid: e.target.value }))} />
            <Input label="Passwort" type="password" placeholder="••••••••"
              value={wifiForm.password}
              onChange={e => setWifiForm(f => ({ ...f, password: e.target.value }))} />
            <div className="flex gap-2">
              <Button loading={wifiSaving} disabled={!wifiForm.ssid} onClick={saveWifi}>
                Speichern
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowWifi(false)}>
                Abbrechen
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Env sections */}
      {sections.map(([section, entries]) => (
        <Card key={section} className="p-6">
          <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-1">
            {SECTION_LABELS[section] ?? section}
          </p>

          {section === "spotify_api" && (
            <SpotifySetupGuide entries={entries} saved={saved} />
          )}

          <div className="space-y-4 mt-4">
            {entries.map(e => (
              <div key={e.key}>
                <div className="flex items-end gap-2">
                  {e.type === "select" ? (
                    <div className="flex-1">
                      <label className="block text-xs font-display font-semibold text-muted mb-1.5">
                        {e.label}
                      </label>
                      <select
                        value={values[e.key] ?? ""}
                        onChange={ev => patch(e.key, ev.target.value)}
                        className="w-full bg-surface border border-border rounded-xl px-3 py-2.5
                                   text-sm text-paper focus:outline-none focus:border-amber
                                   transition-colors"
                      >
                        {e.options?.map(o => (
                          <option key={o} value={o}>{o} kbit/s</option>
                        ))}
                      </select>
                    </div>
                  ) : (
                    <Input
                      label={e.label}
                      type={e.type === "password" ? "password" : "text"}
                      placeholder={
                        e.has_value && e.secret
                          ? "Bereits gesetzt – neu eingeben um zu ändern"
                          : e.description
                      }
                      value={values[e.key] ?? ""}
                      onChange={ev => patch(e.key, ev.target.value)}
                      className="flex-1 font-mono text-sm"
                    />
                  )}
                  <Button
                    size="sm"
                    disabled={!dirty[e.key]}
                    loading={saving[e.key]}
                    onClick={() => save(e.key)}
                  >
                    {saved[e.key] ? "Gespeichert" : "Speichern"}
                  </Button>
                </div>
                <p className="text-xs text-muted mt-1">{e.description}</p>
                {errors[e.key] && (
                  <p className="text-xs text-red-400 mt-1">{errors[e.key]}</p>
                )}
                {e.has_value && e.secret && (
                  <p className="text-xs text-teal/70 mt-0.5">Bereits konfiguriert</p>
                )}
              </div>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}