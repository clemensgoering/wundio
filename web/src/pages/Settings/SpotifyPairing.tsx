import { useState } from "react";
import useSWR from "swr";
import { Button } from "@/components/ui";

interface SpotifyStatus {
  installed:      boolean;
  running:        boolean;
  logged_in:      boolean;
  username:       string;
  device_name:    string;
  playback_ready: boolean;
  pairing:        null | { url: string; code: string; expires_at: string };
}

const fetcher = async (url: string): Promise<SpotifyStatus> => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

function formatExpiry(iso: string): string {
  const d = new Date(iso);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}

export default function SpotifyPairing() {
  const [loggingOut, setLoggingOut] = useState(false);
  const [error, setError] = useState("");

  const { data, mutate } = useSWR<SpotifyStatus>("/api/spotify/status", fetcher, {
    refreshInterval: (d) => (d?.logged_in ? 15_000 : 3_000),
  });

  const logout = async () => {
    if (!window.confirm("Spotify-Konto der Box wirklich entfernen? Danach wird ein neuer Anmeldecode angezeigt.")) return;
    setLoggingOut(true);
    setError("");
    try {
      const r = await fetch("/api/spotify/logout", { method: "POST" });
      if (!r.ok) throw new Error();
      await mutate();
    } catch {
      setError("Abmelden fehlgeschlagen.");
    } finally {
      setLoggingOut(false);
    }
  };

  const box = "bg-surface border border-border rounded-2xl p-5 space-y-4";

  if (!data) {
    return (
      <div className={box}>
        <p className="text-xs text-muted">Lade Spotify-Status…</p>
      </div>
    );
  }

  if (!data.installed || !data.running) {
    return (
      <div className={box}>
        <p className="text-sm font-display font-semibold text-red-400">
          {!data.installed ? "Spotify-Player nicht installiert" : "Spotify-Player läuft nicht"}
        </p>
        <p className="text-xs text-muted">
          {!data.installed
            ? "go-librespot ist auf der Box nicht installiert. Bitte das Setup erneut ausführen."
            : "go-librespot wurde nicht gestartet. Bitte wundio-core neu starten oder die Logs prüfen."}
        </p>
      </div>
    );
  }

  if (data.logged_in) {
    return (
      <div className={box}>
        <div className="bg-teal/10 border border-teal/30 rounded-lg p-3">
          <p className="text-xs text-teal font-semibold">✓ Mit Spotify verbunden</p>
          <p className="text-sm text-paper mt-1">
            Konto: <span className="font-semibold">{data.username || "unbekannt"}</span>
          </p>
          {data.device_name && (
            <p className="text-xs text-muted mt-0.5">
              Gerät: <span className="font-mono">{data.device_name}</span>
            </p>
          )}
        </div>
        {error && <p className="text-xs text-red-400">{error}</p>}
        <Button onClick={logout} loading={loggingOut}>Anderes Konto verwenden</Button>
      </div>
    );
  }

  const p = data.pairing;
  if (!p) {
    return (
      <div className={box}>
        <p className="text-xs text-muted animate-pulse">Warte auf Anmeldecode…</p>
      </div>
    );
  }

  const expiry = formatExpiry(p.expires_at);
  return (
    <div className={box}>
      <div className="text-center space-y-2">
        <p className="text-xs text-muted">Dein Anmeldecode</p>
        <p className="font-mono font-bold text-4xl tracking-widest text-honey select-all">
          {p.code}
        </p>
        {expiry && <p className="text-[10px] text-muted">Gültig bis {expiry} Uhr</p>}
      </div>

      <a href={p.url} target="_blank" rel="noopener noreferrer"
        className="block w-full px-4 py-2.5 rounded-xl bg-teal text-ink text-center
                   font-display font-bold text-sm hover:bg-teal/90 transition-colors">
        Spotify-Link öffnen
      </a>

      <ol className="text-xs text-muted space-y-1 list-decimal list-inside">
        <li>Link öffnen oder spotify.com/pair</li>
        <li>Code eingeben</li>
        <li>Fertig – die Box bleibt angemeldet, kein Handy nötig</li>
      </ol>

      <p className="text-[10px] text-muted">
        Tipp: Lege für die Box ein eigenes Mitglied im Spotify-Familienabo an, damit Eltern und Box gleichzeitig hören können.
      </p>
    </div>
  );
}
