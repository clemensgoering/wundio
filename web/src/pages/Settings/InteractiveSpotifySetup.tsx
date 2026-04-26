"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui";

interface InteractiveSetupProps {
  hasClientId: boolean;
  hasSecret: boolean;
  hasRefreshToken: boolean;
}

export default function InteractiveSpotifySetup({
  hasClientId,
  hasSecret,
  hasRefreshToken,
}: InteractiveSetupProps) {
  const [currentStep, setCurrentStep] = useState(1);
  const [localIp, setLocalIp] = useState("");
  const [ipError, setIpError] = useState("");

  // Auto-detect local IP on mount
  useEffect(() => {
    if (!localIp) {
      fetch("/api/system/status")
        .then((r) => r.json())
        .then((data) => {
          if (data.local_ip && data.local_ip !== "192.168.1.XXX") {
            setLocalIp(data.local_ip);
          }
        })
        .catch(() => {
          // Fallback wenn API nicht erreichbar
          setLocalIp("");
        });
    }
  }, []);

  const validateIp = (ip: string): boolean => {
    setIpError("");
    
    if (!ip.trim()) {
      setIpError("IP-Adresse erforderlich");
      return false;
    }

    // Remove any protocol if user pasted full URL
    const cleanIp = ip
      .replace(/^https?:\/\//, "")  // Remove http:// or https://
      .replace(/:\d+$/, "")          // Remove port
      .trim();

    // Validate IP format
    const ipPattern = /^(\d{1,3}\.){3}\d{1,3}$/;
    if (!ipPattern.test(cleanIp)) {
      setIpError("Ungültiges Format. Nur IP-Adresse (z.B. 192.168.178.112)");
      return false;
    }

    // Validate each octet is 0-255
    const octets = cleanIp.split(".");
    for (const octet of octets) {
      const num = parseInt(octet, 10);
      if (num < 0 || num > 255) {
        setIpError("IP-Adresse ungültig (jede Zahl muss 0-255 sein)");
        return false;
      }
    }

    // Update to cleaned version
    setLocalIp(cleanIp);
    return true;
  };

  const goToStep2 = () => {
    if (validateIp(localIp)) {
      setCurrentStep(2);
    }
  };

  const redirectUri = localIp 
    ? `http://${localIp}:8000/api/spotify/callback`
    : `http://192.168.1.XXX:8000/api/spotify/callback`;
  const credentialsReady = hasClientId && hasSecret;

  return (
    <div className="bg-ink/30 border border-border rounded-2xl p-5 space-y-4">
      <p className="text-xs font-display font-bold text-paper uppercase tracking-wider">
        Spotify Web API Einrichtung
      </p>

      {/* Step 1: Confirm IP */}
      <div className="flex gap-3">
        <div
          className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                      text-[10px] font-bold mt-0.5 transition-colors
                      ${currentStep >= 1 ? "bg-teal text-ink" : "bg-border text-muted"}`}
        >
          1
        </div>
        <div className="flex-1">
          <p className="text-sm font-display font-semibold text-paper mb-1">
            Wundio IP-Adresse bestätigen
          </p>
          
          {currentStep === 1 ? (
            <div className="space-y-3 mt-2">
              <p className="text-xs text-muted">
                Diese IP wird für die Spotify Redirect URI benötigt:
              </p>
              
              <div>
                <input
                  type="text"
                  value={localIp}
                  onChange={(e) => {
                    setLocalIp(e.target.value);
                    setIpError("");
                  }}
                  placeholder="192.168.178.112"
                  className="w-full px-3 py-2 bg-surface border border-border rounded-lg
                             text-sm text-paper font-mono
                             focus:outline-none focus:ring-2 focus:ring-teal/50"
                />
                {ipError && (
                  <p className="text-xs text-red-400 mt-1">{ipError}</p>
                )}
                <p className="text-[10px] text-muted/60 mt-1">
                  Nur die IP-Adresse eingeben (kein http://, kein Port)
                </p>
              </div>

              <div className="bg-surface/50 border border-border/50 rounded-lg p-3">
                <p className="text-xs text-muted mb-1">Resultierende Redirect URI:</p>
                <code className="text-xs font-mono text-honey select-all break-all">
                  {redirectUri}
                </code>
              </div>

              <Button onClick={goToStep2} className="w-full">
                Weiter zu Schritt 2 →
              </Button>
            </div>
          ) : (
            <div className="text-xs text-muted space-y-1">
              <p>✓ IP-Adresse: <code className="text-honey font-mono">{localIp}</code></p>
              <button
                onClick={() => setCurrentStep(1)}
                className="text-teal underline underline-offset-2 hover:text-teal/80"
              >
                Bearbeiten
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Step 2: Create Spotify App */}
      <div className="flex gap-3">
        <div
          className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                      text-[10px] font-bold mt-0.5 transition-colors
                      ${currentStep >= 2 ? "bg-teal text-ink" : "bg-border text-muted"}`}
        >
          2
        </div>
        <div className="flex-1">
          <p className="text-sm font-display font-semibold text-paper mb-1">
            Spotify Developer App anlegen
          </p>
          
          {currentStep >= 2 ? (
            <div className="space-y-3 mt-2">
              <p className="text-xs text-muted">
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

              <div className="bg-surface border border-border rounded-xl p-3 text-xs space-y-2">
                <div>
                  <span className="text-paper font-semibold">App Name:</span>{" "}
                  <span className="text-muted">Wundio (beliebig)</span>
                </div>
                <div>
                  <span className="text-paper font-semibold">Description:</span>{" "}
                  <span className="text-muted">Home music box (beliebig)</span>
                </div>
                <div>
                  <span className="text-paper font-semibold block mb-1">Redirect URI:</span>
                  <div className="bg-ink/40 rounded p-2 border border-border/50">
                    <code className="text-honey font-mono text-[11px] select-all break-all">
                      {redirectUri}
                    </code>
                  </div>
                  <p className="text-red-400 text-[10px] mt-1 font-semibold">
                    ⚠️ Exakt diese URI in der Spotify App eintragen!
                  </p>
                </div>
              </div>

              <Button onClick={() => setCurrentStep(3)} className="w-full">
                App angelegt → Weiter zu Schritt 3
              </Button>
            </div>
          ) : (
            <p className="text-xs text-muted/60 italic">
              Erst IP-Adresse in Schritt 1 bestätigen
            </p>
          )}
        </div>
      </div>

      {/* Step 3: Enter Credentials */}
      <div className="flex gap-3">
        <div
          className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                      text-[10px] font-bold mt-0.5 transition-colors
                      ${currentStep >= 3 ? "bg-teal text-ink" : "bg-border text-muted"}`}
        >
          3
        </div>
        <div className="flex-1">
          <p className="text-sm font-display font-semibold text-paper mb-1">
            Client ID & Secret eintragen
          </p>
          
          {currentStep >= 3 ? (
            <div className="space-y-2 mt-2">
              <p className="text-xs text-muted">
                Im Spotify Dashboard → Settings → Client ID & Client Secret kopieren
                und oben in den SPOTIFY_CLIENT_ID / SPOTIFY_CLIENT_SECRET Feldern eintragen.
              </p>
              {credentialsReady && (
                <Button onClick={() => setCurrentStep(4)} className="w-full">
                  Credentials gespeichert → Weiter zu Schritt 4
                </Button>
              )}
            </div>
          ) : (
            <p className="text-xs text-muted/60 italic">
              Erst Schritt 2 abschließen
            </p>
          )}
        </div>
      </div>

      {/* Step 4: Authorize */}
      <div className="flex gap-3">
        <div
          className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center
                      text-[10px] font-bold mt-0.5 transition-colors
                      ${hasRefreshToken ? "bg-teal text-ink" : currentStep >= 4 ? "bg-honey text-white" : "bg-border text-muted"}`}
        >
          4
        </div>
        <div className="flex-1">
          <p className="text-sm font-display font-semibold text-paper mb-1">
            Mit Spotify autorisieren
          </p>
          
          {currentStep >= 4 ? (
            hasRefreshToken ? (
              <div className="bg-teal/10 border border-teal/30 rounded-lg p-3 mt-2">
                <p className="text-xs text-teal font-semibold">
                  ✓ Spotify erfolgreich verbunden!
                </p>
                <p className="text-[10px] text-muted mt-1">
                  Refresh Token gespeichert. RFID-Tags können jetzt Playlists starten.
                </p>
              </div>
            ) : (
              <div className="space-y-2 mt-2">
                <p className="text-xs text-muted">
                  Klicke auf "Mit Spotify verbinden" um den OAuth-Flow zu starten:
                </p>
                <a
                  href="/api/spotify/auth/start"
                  className="block w-full px-4 py-2.5 rounded-xl bg-teal text-ink text-center
                             font-display font-bold text-sm
                             hover:bg-teal/90 transition-colors"
                >
                  Mit Spotify verbinden
                </a>
                <p className="text-[10px] text-muted/60">
                  Du wirst zu Spotify weitergeleitet und nach Autorisierung zurückgeleitet.
                </p>
              </div>
            )
          ) : (
            <p className="text-xs text-muted/60 italic">
              Erst Schritt 3 abschließen
            </p>
          )}
        </div>
      </div>
    </div>
  );
}