import { useState, useEffect } from "react";
import { Button, Input } from "@/components/ui";

const RELAY_REDIRECT_URI = "https://wundio.dev/spotify-callback";

interface InteractiveSetupProps {
  hasClientId:        boolean;
  hasSecret:          boolean;
  hasRefreshToken:    boolean;
  onCredentialsSaved?: () => void;
}

export default function InteractiveSpotifySetup({
  hasClientId: initialHasClientId,
  hasSecret: initialHasSecret,
  hasRefreshToken,
  onCredentialsSaved,
}: InteractiveSetupProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [localIp, setLocalIp] = useState("");
  const [ipError, setIpError] = useState("");
  const [clientId, setClientId] = useState("");
  const [clientSecret, setClientSecret] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [hasClientId, setHasClientId] = useState(initialHasClientId);
  const [hasSecret, setHasSecret] = useState(initialHasSecret);

  const credentialsReady = hasClientId && hasSecret;

  useEffect(() => setHasClientId(initialHasClientId), [initialHasClientId]);
  useEffect(() => setHasSecret(initialHasSecret), [initialHasSecret]);
  useEffect(() => {
    if (initialHasClientId && initialHasSecret && currentStep < 4) setCurrentStep(4);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    fetch("/api/system/status")
      .then((r) => r.json())
      .then((d) => { if (d.local_ip && !d.local_ip.includes("XXX")) setLocalIp(d.local_ip); })
      .catch(() => {});
  }, []);

  const validateIp = (ip: string): boolean => {
    setIpError("");
    const clean = ip.replace(/^https?:\/\//, "").replace(/:\d+$/, "").trim();
    if (!clean) { setIpError("IP-Adresse erforderlich"); return false; }
    const ok = /^(\d{1,3}\.){3}\d{1,3}$/.test(clean) &&
      clean.split(".").every((o) => +o >= 0 && +o <= 255);
    if (!ok) { setIpError("Ungültiges Format (z.B. 192.168.178.112)"); return false; }
    setLocalIp(clean);
    return true;
  };

  const confirmIp = async () => {
    if (!validateIp(localIp)) return;
    try {
      await fetch("/api/settings/env/PI_LOCAL_IP", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ value: localIp.trim() }),
      });
    } catch { /* non-fatal */ }
    setCurrentStep(2);
  };

  const saveCredentials = async () => {
    setSaveError("");
    if (!clientId.trim() || !clientSecret.trim()) {
      setSaveError("Bitte Client ID und Secret ausfüllen.");
      return;
    }
    setSaving(true);
    try {
      const [idRes, secretRes] = await Promise.all([
        fetch("/api/settings/env/SPOTIFY_CLIENT_ID", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: clientId.trim() }),
        }),
        fetch("/api/settings/env/SPOTIFY_CLIENT_SECRET", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ value: clientSecret.trim() }),
        }),
      ]);
      if (idRes.ok && secretRes.ok) {
        setHasClientId(true);
        setHasSecret(true);
        setClientId("");
        setClientSecret("");
        setCurrentStep(4);
        onCredentialsSaved?.();
      } else {
        setSaveError("Fehler beim Speichern.");
      }
    } catch {
      setSaveError("Netzwerkfehler.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-surface border border-border rounded-2xl p-5 space-y-5">
      <Step num={1} active={currentStep >= 1} done={currentStep > 1} title="Pi IP-Adresse bestätigen">
        {currentStep === 1 ? (
          <div className="space-y-3 mt-2">
            <p className="text-xs text-muted">
              Wird benötigt damit der Spotify-Callback nach der Autorisierung zurück zur Box findet.
            </p>
            <div>
              <input type="text" value={localIp}
                onChange={(e) => { setLocalIp(e.target.value); setIpError(""); }}
                placeholder="192.168.178.112"
                className="w-full px-3 py-2 bg-surface border border-border rounded-lg
                           text-sm text-paper font-mono focus:outline-none focus:ring-2 focus:ring-teal/50"
              />
              {ipError && <p className="text-xs text-red-400 mt-1">{ipError}</p>}
            </div>
            <Button onClick={confirmIp} className="w-full">Bestätigen →</Button>
          </div>
        ) : (
          <DoneRow label={`IP: ${localIp}`} onEdit={() => setCurrentStep(1)} />
        )}
      </Step>

      <Step num={2} active={currentStep >= 2} done={currentStep > 2} title="Spotify Developer App anlegen">
        {currentStep >= 2 ? (
          currentStep > 2 ? (
            <DoneRow label="App angelegt" onEdit={() => setCurrentStep(2)} />
          ) : (
            <div className="space-y-3 mt-2">
              <p className="text-xs text-muted">
                Gehe zu{" "}
                <a href="https://developer.spotify.com/dashboard" target="_blank"
                  rel="noopener noreferrer" className="text-teal underline underline-offset-2">
                  developer.spotify.com/dashboard
                </a>{" "}→ "Create app" und trage diese Redirect URI ein:
              </p>
              <div className="bg-ink/30 border border-border/50 rounded-xl p-3 text-xs">
                <div className="flex items-center gap-2 bg-ink/40 rounded p-2">
                  <code className="text-honey font-mono text-[11px] select-all break-all flex-1">
                    {RELAY_REDIRECT_URI}
                  </code>
                  <button onClick={() => navigator.clipboard.writeText(RELAY_REDIRECT_URI)}
                    className="text-[10px] text-muted hover:text-paper px-2 py-1 border border-border rounded flex-shrink-0">
                    Kopieren
                  </button>
                </div>
                <p className="text-teal text-[10px] mt-2">✓ HTTPS – wird von Spotify akzeptiert</p>
              </div>
              <Button onClick={() => setCurrentStep(3)} className="w-full">App angelegt → Weiter</Button>
            </div>
          )
        ) : (
          <p className="text-xs text-muted/60 italic mt-1">Erst Schritt 1 abschließen</p>
        )}
      </Step>

      <Step num={3} active={currentStep >= 3} done={credentialsReady && currentStep > 3} title="Client ID & Secret eintragen">
        {currentStep >= 3 ? (
          credentialsReady && currentStep >= 4 ? (
            <div className="space-y-2 mt-2">
              <div className="bg-teal/10 border border-teal/30 rounded-lg p-3">
                <p className="text-xs text-teal font-semibold">✓ Credentials gespeichert</p>
              </div>
              <button onClick={() => { setHasClientId(false); setHasSecret(false); setCurrentStep(3); }}
                className="text-xs text-teal underline underline-offset-2">Neu eingeben</button>
            </div>
          ) : (
            <div className="space-y-3 mt-2">
              <p className="text-xs text-muted">Im Spotify Dashboard → Settings → kopieren:</p>
              <div>
                <label className="block text-xs font-semibold text-muted mb-1">Client ID</label>
                <Input type="text" placeholder="Paste Client ID..." value={clientId}
                  onChange={(e) => setClientId(e.target.value)} className="font-mono text-xs" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-muted mb-1">Client Secret</label>
                <Input type="password" placeholder="Paste Client Secret..." value={clientSecret}
                  onChange={(e) => setClientSecret(e.target.value)} className="font-mono text-xs" />
              </div>
              {saveError && <p className="text-xs text-red-400">{saveError}</p>}
              <Button onClick={saveCredentials} loading={saving}
                disabled={!clientId.trim() || !clientSecret.trim()} className="w-full">
                Speichern & weiter
              </Button>
            </div>
          )
        ) : (
          <p className="text-xs text-muted/60 italic mt-1">Erst Schritt 2 abschließen</p>
        )}
      </Step>

      <Step num={4} active={currentStep >= 4} done={hasRefreshToken} title="Mit Spotify autorisieren">
        {currentStep >= 4 ? (
          hasRefreshToken ? (
            <div className="bg-teal/10 border border-teal/30 rounded-lg p-3 mt-2">
              <p className="text-xs text-teal font-semibold">✓ Spotify verbunden!</p>
              <p className="text-[10px] text-muted mt-1">RFID-Tags können jetzt Playlists starten.</p>
            </div>
          ) : (
            <div className="space-y-2 mt-2">
              <p className="text-xs text-muted">
                Klicke auf den Button. Du wirst zu Spotify weitergeleitet, dann zurück zur Box.
              </p>
              <a href="/api/spotify/auth/start"
                className="block w-full px-4 py-2.5 rounded-xl bg-teal text-ink text-center
                           font-display font-bold text-sm hover:bg-teal/90 transition-colors">
                Mit Spotify verbinden
              </a>
            </div>
          )
        ) : (
          <p className="text-xs text-muted/60 italic mt-1">Erst Schritt 3 abschließen</p>
        )}
      </Step>
    </div>
  );
}

function Step({ num, active, done, title, children }: {
  num: number; active: boolean; done: boolean; title: string; children: React.ReactNode;
}) {
  return (
    <div className="flex gap-3">
      <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                       text-[10px] font-bold mt-0.5 transition-colors
                       ${done ? "bg-teal text-ink" : active ? "bg-honey text-white" : "bg-border text-muted"}`}>
        {done ? "✓" : num}
      </div>
      <div className="flex-1">
        <p className="text-sm font-display font-semibold text-paper">{title}</p>
        {children}
      </div>
    </div>
  );
}

function DoneRow({ label, onEdit }: { label: string; onEdit: () => void }) {
  return (
    <div className="flex items-center gap-3 mt-1">
      <p className="text-xs text-muted flex-1">✓ {label}</p>
      <button onClick={onEdit} className="text-xs text-teal underline underline-offset-2">Bearbeiten</button>
    </div>
  );
}