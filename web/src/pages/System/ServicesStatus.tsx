// web/src/pages/System/ServicesStatus.tsx

import { Card } from "@/components/ui";
import useSWR from "swr";

interface ServiceInfo {
  active: boolean;
  since:  string;
}

interface SpotifyDevice {
  found:     boolean;
  name:      string;
  is_active: boolean;
  error:     string;
}

interface ServicesData {
  services: {
    "wundio-core":      ServiceInfo;
    "wundio-librespot": ServiceInfo;
  };
  spotify_device: SpotifyDevice;
}

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export default function ServicesStatus() {
  const { data, isLoading } = useSWR<ServicesData>(
    "/api/system/services",
    fetcher,
    { refreshInterval: 10_000 },
  );

  return (
    <div>
      <h2 className="font-display font-bold text-xl text-paper mb-3">Dienste</h2>
      <Card className="divide-y divide-border">

        {/* wundio-core */}
        <ServiceRow
          label="wundio-core"
          description="Haupt-Dienst (FastAPI + RFID-Loop)"
          active={data?.services["wundio-core"]?.active}
          since={data?.services["wundio-core"]?.since}
          loading={isLoading}
        />

        {/* wundio-librespot */}
        <ServiceRow
          label="librespot"
          description="Spotify Connect Prozess (läuft als Teil von wundio-core)"
          active={data?.services["wundio-librespot"]?.active}
          since={data?.services["wundio-librespot"]?.since}
          loading={isLoading}
        />

        {/* Spotify Device visibility */}
        <div className="p-4">
          <div className="flex items-start gap-3">
            <div className="flex-shrink-0 mt-0.5">
              {isLoading ? (
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-border animate-pulse" />
              ) : data?.spotify_device.found ? (
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-teal" />
              ) : (
                <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <p className="text-sm font-display font-semibold text-paper">
                  Spotify-Gerät
                </p>
                {data?.spotify_device.found && (
                  <span className="text-[10px] font-mono bg-surface border border-border
                                   text-muted px-2 py-0.5 rounded-full">
                    {data.spotify_device.name}
                  </span>
                )}
                {data?.spotify_device.is_active && (
                  <span className="text-[10px] font-display font-bold text-teal
                                   bg-teal/10 border border-teal/20 px-2 py-0.5 rounded-full">
                    AKTIV
                  </span>
                )}
              </div>
              <p className="text-xs text-muted mt-0.5">
                {isLoading
                  ? "Prüfe Spotify-Geräteliste..."
                  : data?.spotify_device.found
                  ? data.spotify_device.is_active
                    ? "Bereit – Wiedergabe wird auf diesen Pi gelenkt."
                    : "Gerät registriert. Wird bei nächstem RFID-Scan aktiviert."
                  : data?.spotify_device.error || "Gerät nicht sichtbar."}
              </p>
              {data && !data.spotify_device.found && !data.spotify_device.error.includes("nicht konfiguriert") && (
                <p className="text-[10px] text-amber/80 mt-1">
                  Öffne einmalig die Spotify-App → "Gerät auswählen" → wähle{" "}
                  <strong className="text-paper">Wundio</strong> um librespot zu registrieren.
                </p>
              )}
            </div>
          </div>
        </div>

      </Card>
    </div>
  );
}

// ── ServiceRow helper ─────────────────────────────────────────────────────────

function ServiceRow({
  label, description, active, since, loading,
}: {
  label:       string;
  description: string;
  active?:     boolean;
  since?:      string;
  loading:     boolean;
}) {
  return (
    <div className="p-4 flex items-start gap-3">
      <div className="flex-shrink-0 mt-1">
        {loading ? (
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-border animate-pulse" />
        ) : active ? (
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-teal" />
        ) : (
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-display font-semibold text-paper">{label}</p>
          <span className={`text-[10px] font-display font-bold px-2 py-0.5 rounded-full border
                            ${active
                              ? "text-teal bg-teal/10 border-teal/20"
                              : "text-red-400 bg-red-500/10 border-red-500/20"}`}>
            {loading ? "…" : active ? "AKTIV" : "INAKTIV"}
          </span>
        </div>
        <p className="text-xs text-muted mt-0.5">{description}</p>
        {since && active && (
          <p className="text-[10px] text-muted/50 mt-0.5 font-mono">seit {since}</p>
        )}
      </div>
    </div>
  );
}
