import { useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { Button, Card } from "@/components/ui";

interface LearnState {
  armed:       boolean;
  seconds_left: number;
  auto_learn:  boolean;
  now_playing: null | { uri: string; label: string };
}

const fetcher = async (url: string): Promise<LearnState> => {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
};

export default function CardLearning({ onLearned }: { onLearned: () => void }) {
  const [busy,  setBusy]  = useState(false);
  const [error, setError] = useState("");

  const { data, mutate } = useSWR<LearnState>("/api/rfid/learn", fetcher, {
    refreshInterval: (d) => (d?.armed ? 2_000 : 5_000),
  });

  // Revalidate tag list when armed flips true -> false
  const wasArmed = useRef(false);
  useEffect(() => {
    if (!data) return;
    if (wasArmed.current && !data.armed) onLearned();
    wasArmed.current = data.armed;
  }, [data?.armed]);

  const call = async (method: "POST" | "DELETE") => {
    setBusy(true); setError("");
    try {
      const r = await fetch("/api/rfid/learn", {
        method,
        headers: { "Content-Type": "application/json" },
        body: method === "POST" ? JSON.stringify({ seconds: 60 }) : undefined,
      });
      if (!r.ok) throw new Error();
      await mutate();
    } catch {
      setError("Aktion fehlgeschlagen.");
    } finally {
      setBusy(false);
    }
  };

  const playing = data?.now_playing;

  return (
    <Card className="p-5 space-y-3">
      <h2 className="font-display font-bold text-lg text-paper">Karte anlernen</h2>

      {playing ? (
        <p className="text-sm text-teal">Läuft gerade: {playing.label}</p>
      ) : (
        <p className="text-sm text-muted">
          Gerade läuft nichts – starte in der Spotify-App ein Hörspiel auf „Wundio“
        </p>
      )}

      <p className="text-xs text-muted">
        Unbekannte Karte auflegen, während etwas läuft → wird automatisch gespeichert.
      </p>

      {data?.armed ? (
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-amber">
            <span className="inline-block w-2 h-2 rounded-full bg-amber animate-pulse mr-1.5" />
            Halte jetzt die Karte an die Box ({data.seconds_left} s)
          </p>
          <Button variant="secondary" size="sm" loading={busy} onClick={() => call("DELETE")}>
            Abbrechen
          </Button>
        </div>
      ) : (
        <Button variant="secondary" size="sm" loading={busy} onClick={() => call("POST")}>
          Bestehende Karte neu belegen (60 s)
        </Button>
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}
    </Card>
  );
}
