import { useState, useEffect } from "react";
import useSWR from "swr";
import { api } from "@/lib/api";
import { Button, Card, Input, Spinner, Badge } from "@/components/ui";
import type { SystemStatus } from "@/types/api";

export default function Settings() {
  const { data: status, mutate } = useSWR<SystemStatus>(
    "status", () => api.status() as Promise<SystemStatus>, { refreshInterval: 10000 }
  );

  const [wifi, setWifi]   = useState({ ssid: "", password: "" });
  const [saving, setSaving] = useState<string | null>(null);
  const [saved,  setSaved]  = useState<string | null>(null);
  const [spotifyName, setSpotifyName] = useState("Wundio");

  // Load spotify device name from settings
  useEffect(() => {
    api.getSetting("spotify_device_name")
      .then((r: any) => { if (r.value) setSpotifyName(r.value); })
      .catch(() => {});
  }, []);

  const saveSetting = async (key: string, value: string, label: string) => {
    setSaving(label); setSaved(null);
    await api.setSetting(key, value);
    setSaving(null); setSaved(label);
    setTimeout(() => setSaved(null), 2000);
  };

  const completeSetup = async () => {
    setSaving("setup");
    await api.completeSetup();
    await mutate();
    setSaving(null);
  };

  if (!status) return <div className="flex items-center justify-center h-64"><Spinner size={32} /></div>;

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="font-display font-extrabold text-3xl text-paper mb-1">Einstellungen</h1>
        <p className="text-muted text-sm">System und Netzwerk konfigurieren</p>
      </div>

      {/* Setup Status */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider">Setup Status</p>
          <Badge color={status.setup_complete ? "teal" : "amber"}>
            {status.setup_complete ? "Abgeschlossen" : "Ausstehend"}
          </Badge>
        </div>
        <div className="space-y-2 text-sm mb-5">
          <InfoRow label="Version"          value={`v${status.version}`} />
          <InfoRow label="Modell"           value={status.hardware.model || "—"} />
          <InfoRow label="RAM"              value={`${status.hardware.ram_mb} MB`} />
          <InfoRow label="Hotspot aktiv"    value={status.hotspot_active ? "Ja" : "Nein"} />
        </div>
        {!status.setup_complete && (
          <Button onClick={completeSetup} loading={saving === "setup"}>
            Setup abschließen
          </Button>
        )}
      </Card>

      {/* WiFi */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">WLAN</p>
        <p className="text-xs text-muted mb-4">
          Nach dem Speichern verbindet sich Wundio mit dem neuen Netzwerk.
          Verbinde dich danach mit der neuen IP-Adresse.
        </p>
        <div className="space-y-3 mb-4">
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
        </div>
        <div className="flex items-center gap-3">
          <Button
            disabled={!wifi.ssid}
            loading={saving === "wifi"}
            onClick={async () => {
              setSaving("wifi");
              await api.setSetting("wifi_ssid", wifi.ssid);
              await api.setSetting("wifi_password", wifi.password);
              await api.setSetting("wifi_configured", "true");
              setSaving(null); setSaved("wifi");
              setTimeout(() => setSaved(null), 2000);
            }}
          >
            WLAN speichern
          </Button>
          {saved === "wifi" && <span className="text-xs text-teal">✓ Gespeichert</span>}
        </div>
      </Card>

      {/* Spotify */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">Spotify</p>
        <p className="text-xs text-muted mb-4">
          Name des Geräts wie er in der Spotify-App erscheint.
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
        {saved === "spotify" && <p className="text-xs text-teal mt-2">✓ Gespeichert – Neustart empfohlen</p>}
      </Card>

      {/* Features */}
      <Card className="p-6">
        <p className="text-xs font-display font-semibold text-muted uppercase tracking-wider mb-4">
          Aktive Features
        </p>
        <p className="text-xs text-muted mb-4">
          Features werden automatisch anhand des Pi-Modells aktiviert.
          Manuelle Überschreibung via <code className="text-teal bg-black/40 px-1 rounded">/etc/wundio/wundio.env</code>.
        </p>
        <div className="grid grid-cols-2 gap-3">
          {Object.entries(status.features).map(([key, enabled]) => (
            <div key={key} className="flex items-center gap-2.5">
              <span className={`w-2 h-2 rounded-full flex-shrink-0 ${enabled ? "bg-teal" : "bg-border"}`} />
              <span className={`text-sm ${enabled ? "text-paper/70" : "text-muted/40"}`}>
                {key.replace(/_/g, " ")}
              </span>
              {enabled
                ? <Badge color="teal">AN</Badge>
                : <Badge color="muted">AUS</Badge>}
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
