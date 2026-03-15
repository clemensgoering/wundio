import { useState, useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Button, Card, Input, Spinner, Badge } from "@/components/ui";
import type { SystemStatus } from "@/types/api";

interface WifiStatus { configured: boolean; ssid: string; hotspot: boolean; }

export default function Settings() {
  const { data: status, mutate } = useSWR<SystemStatus>(
    "status", () => api.status() as Promise<SystemStatus>, { refreshInterval: 10000 }
  );
  const { data: wifiStatus } = useSWR<WifiStatus>(
    "wifi-status", () => fetch("/api/wifi/status").then(r => r.json()),
    { refreshInterval: 15000 }
  );

  const [wifi, setWifi]         = useState({ ssid: "", password: "" });
  const [saving, setSaving]     = useState<string | null>(null);
  const [saved,  setSaved]      = useState<string | null>(null);
  const [spotifyName, setSpotifyName] = useState("Wundio");
  const [showWifiForm, setShowWifiForm] = useState(false);

  useEffect(() => {
    api.getSetting("spotify_device_name")
      .then((r: any) => { if (r.value) setSpotifyName(r.value); })
      .catch(() => {});
  }, []);

  const saveSetting = async (key: string, value: string, label: string) => {
    setSaving(label);
    await api.setSetting(key, value);
    setSaving(null); setSaved(label);
    setTimeout(() => setSaved(null), 2500);
  };

  if (!status) return <div className="flex items-center justify-center h-64"><Spinner size={32} /></div>;

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Einstellungen</h1>
        <p className="text-muted text-sm">System und Netzwerk konfigurieren</p>
      </div>

      {/* System status */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider">System</p>
          <Badge color={status.setup_complete ? "teal" : "amber"}>
            {status.setup_complete ? "Bereit" : "Setup ausstehend"}
          </Badge>
        </div>
        <div className="space-y-2 text-sm">
          <InfoRow label="Version"    value={`v${status.version}`} />
          <InfoRow label="Hardware"   value={status.hardware.model || "—"} />
          <InfoRow label="RAM"        value={`${status.hardware.ram_mb} MB`} />
          <InfoRow label="Pi Gen"     value={`${status.hardware.pi_generation}`} />
        </div>
        {!status.setup_complete && (
          <div className="mt-4">
            <Button loading={saving === "setup"} onClick={async () => {
              setSaving("setup");
              await api.completeSetup();
              await mutate();
              setSaving(null);
            }}>
              Setup abschliessen
            </Button>
          </div>
        )}
      </Card>

      {/* WiFi - shows current connection, allows change */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider">WLAN</p>
          {wifiStatus && (
            <Badge color={wifiStatus.configured ? "teal" : "amber"}>
              {wifiStatus.configured ? "Verbunden" : "Nicht konfiguriert"}
            </Badge>
          )}
        </div>

        {wifiStatus?.configured && wifiStatus.ssid && (
          <div className="mb-4 bg-teal/5 border border-teal/20 rounded-xl px-4 py-3">
            <p className="text-xs text-muted mb-0.5">Aktuelles Netzwerk</p>
            <p className="font-display font-semibold text-paper">{wifiStatus.ssid}</p>
          </div>
        )}

        {!showWifiForm ? (
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowWifiForm(true)}
          >
            {wifiStatus?.configured ? "Netzwerk wechseln" : "WLAN einrichten"}
          </Button>
        ) : (
          <div className="space-y-3">
            <p className="text-xs text-muted">
              Nach dem Speichern verbindet sich Wundio mit dem neuen Netzwerk.
              Danach ist das Gerät unter der neuen IP erreichbar.
            </p>
            <Input
              label="SSID (Netzwerkname)"
              placeholder="MeinHeimnetz"
              value={wifi.ssid}
              onChange={e => setWifi(w => ({ ...w, ssid: e.target.value }))}
            />
            <Input
              label="Passwort"
              type="password"
              placeholder="••••••••"
              value={wifi.password}
              onChange={e => setWifi(w => ({ ...w, password: e.target.value }))}
            />
            <div className="flex items-center gap-2">
              <Button
                disabled={!wifi.ssid}
                loading={saving === "wifi"}
                onClick={async () => {
                  setSaving("wifi");
                  try {
                    await fetch("/api/wifi/configure", {
                      method: "POST",
                      headers: { "Content-Type": "application/json" },
                      body: JSON.stringify({ ssid: wifi.ssid, password: wifi.password }),
                    });
                    setSaved("wifi");
                    setShowWifiForm(false);
                    setTimeout(() => setSaved(null), 2500);
                  } finally { setSaving(null); }
                }}
              >
                Speichern
              </Button>
              <Button variant="ghost" size="sm" onClick={() => setShowWifiForm(false)}>
                Abbrechen
              </Button>
              {saved === "wifi" && <span className="text-xs text-teal">Gespeichert</span>}
            </div>
          </div>
        )}
      </Card>

      {/* Spotify */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">Spotify</p>
        <p className="text-xs text-muted mb-4">
          Name des Geräts in der Spotify App.
          Wundio erscheint automatisch als Lautsprecher, sobald Spotify Premium aktiv ist
          und App und Pi im gleichen Netzwerk sind.
        </p>
        <div className="flex items-end gap-3">
          <Input
            label="Gerätename"
            placeholder="Wundio"
            value={spotifyName}
            onChange={e => setSpotifyName(e.target.value)}
            className="flex-1"
          />
          <Button
            loading={saving === "spotify"}
            onClick={() => saveSetting("spotify_device_name", spotifyName, "spotify")}
          >
            Speichern
          </Button>
        </div>
        {saved === "spotify" && <p className="text-xs text-teal mt-2">Gespeichert – Neustart empfohlen</p>}
      </Card>

      {/* Features */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-3">
          Aktive Features
        </p>
        <p className="text-xs text-muted mb-4">
          Automatisch erkannt basierend auf dem Pi-Modell.
          Manuell überschreibbar in{" "}
          <code className="text-teal bg-black/40 px-1 rounded">/etc/wundio/wundio.env</code>.
        </p>
        <div className="grid grid-cols-2 gap-2.5">
          {Object.entries(status.features).map(([key, enabled]) => (
            <div key={key} className="flex items-center gap-2">
              <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${enabled ? "bg-teal" : "bg-border"}`} />
              <span className={`text-sm ${enabled ? "text-paper/70" : "text-muted/40"}`}>
                {key.replace(/_/g, " ")}
              </span>
              <Badge color={enabled ? "teal" : "muted"}>{enabled ? "An" : "Aus"}</Badge>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-muted">{label}</span>
      <span className="text-paper/70 font-mono text-xs">{value}</span>
    </div>
  );
}