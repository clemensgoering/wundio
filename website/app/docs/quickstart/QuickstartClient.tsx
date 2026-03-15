"use client";

import { useState } from "react";
import { DocHeader, InfoBox } from "@/components/DocComponents";

// ── Pi model data ──────────────────────────────────────────────────────────
const PI_MODELS = [
  {
    id: "pi3",
    label: "Raspberry Pi 3",
    sub: "Model B / B+",
    emoji: "🟢",
    arch: "32-bit (armv7l) oder 64-bit (aarch64)",
    osRecommended: "Raspberry Pi OS Bookworm – 64-bit Lite",
    osNote: "Wähle unbedingt die 64-bit Version – die 32-bit Legacy-Version wird von Wundio nicht empfohlen.",
    features: ["Spotify", "RFID", "OLED", "Buttons", "Web-Interface"],
    limitations: ["Kein lokales LLM", "Kein erweitertes KI"],
    ram: "1 GB",
    installNote: null,
  },
  {
    id: "pi4",
    label: "Raspberry Pi 4",
    sub: "2 GB / 4 GB / 8 GB",
    emoji: "🔵",
    arch: "64-bit (aarch64)",
    osRecommended: "Raspberry Pi OS Bookworm – 64-bit Lite",
    osNote: "Immer die 64-bit Version wählen für optimale Performance.",
    features: ["Spotify", "RFID", "OLED", "Buttons", "Web-Interface", "Cloud KI", "Erweiterte Spiele"],
    limitations: ["Kein lokales LLM (außer 8 GB Modell)"],
    ram: "2–8 GB",
    installNote: "Für 8 GB Modelle: Ollama LLM ist optional installierbar.",
  },
  {
    id: "pi5",
    label: "Raspberry Pi 5",
    sub: "4 GB / 8 GB",
    emoji: "🟣",
    arch: "64-bit (aarch64)",
    osRecommended: "Raspberry Pi OS Bookworm – 64-bit Lite",
    osNote: "Empfohlen für alle KI-Features inkl. lokalem LLM.",
    features: ["Spotify", "RFID", "OLED", "Buttons", "Web-Interface", "Cloud KI", "Lokales LLM (Ollama)", "Alle Features"],
    limitations: [],
    ram: "4–8 GB",
    installNote: "Lokales LLM (llama3.2:3b) nach der Installation mit install-ollama.sh aktivierbar.",
  },
] as const;

type PiId = typeof PI_MODELS[number]["id"];

// ── Helper components ──────────────────────────────────────────────────────

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="inline-block bg-sand border border-border rounded-lg
                    px-2 py-0.5 font-mono text-xs text-charcoal shadow-sm">
      {children}
    </kbd>
  );
}

function Tag({ color, children }: { color: "green" | "red" | "blue"; children: React.ReactNode }) {
  const cls = {
    green: "bg-mint/12 text-mint border-mint/25",
    red:   "bg-coral/12 text-coral border-coral/25",
    blue:  "bg-sky/12 text-sky-600 border-sky/25",
  }[color];
  return (
    <span className={`inline-block text-[10px] font-display font-bold border rounded-full px-2 py-0.5 ${cls}`}>
      {children}
    </span>
  );
}

function StepBox({ num, title, children }: {
  num: string; title: string; children: React.ReactNode;
}) {
  return (
    <div className="flex gap-5 mb-10">
      <div className="flex flex-col items-center gap-1 flex-shrink-0">
        <div className="w-10 h-10 rounded-2xl bg-honey flex items-center justify-center
                        font-display font-black text-white text-sm shadow-soft flex-shrink-0">
          {num}
        </div>
        <div className="w-0.5 flex-1 bg-border min-h-4" />
      </div>
      <div className="flex-1 pb-2">
        <h2 className="font-display font-bold text-xl text-ink mb-3">{title}</h2>
        <div className="space-y-3">{children}</div>
      </div>
    </div>
  );
}

function Code({ children }: { children: string }) {
  const [copied, setCopied] = useState(false);
  const copy = () => {
    navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div className="relative group">
      <div className="bg-ink rounded-2xl px-5 py-4 font-mono text-sm text-white/85
                      overflow-x-auto pr-16">
        <span className="text-honey/50 select-none mr-2">$</span>
        <span className="select-all">{children}</span>
      </div>
      <button onClick={copy}
              className="absolute right-3 top-1/2 -translate-y-1/2
                         bg-white/10 hover:bg-white/20 text-white/60 hover:text-white
                         text-xs font-display px-2.5 py-1 rounded-lg transition-all">
        {copied ? "✓" : "Kopieren"}
      </button>
    </div>
  );
}

function Screenshot({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="border border-border rounded-2xl overflow-hidden">
      <div className="bg-sand px-4 py-2 border-b border-border flex items-center gap-2">
        <div className="flex gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-coral/50" />
          <span className="w-2.5 h-2.5 rounded-full bg-honey/50" />
          <span className="w-2.5 h-2.5 rounded-full bg-mint/50" />
        </div>
        <span className="text-xs text-muted font-mono">{label}</span>
      </div>
      <div className="bg-white p-5 text-sm font-body">{children}</div>
    </div>
  );
}

// ── Main component ─────────────────────────────────────────────────────────

export function QuickstartClient() {
  const [selectedPi, setSelectedPi] = useState<PiId | null>(null);
  const pi = PI_MODELS.find(m => m.id === selectedPi) ?? null;

  return (
    <div>
      <DocHeader
        chip="Quickstart"
        title="Wundio einrichten"
        desc="Schritt-für-Schritt Anleitung – von der leeren SD-Karte zur fertigen Box. Auch ohne technische Erfahrung umsetzbar."
      />

      {/* ── Pi Selector ──────────────────────────────────────────────────── */}
      <div className="mb-10">
        <p className="text-sm font-display font-bold text-charcoal mb-3">
          Welches Raspberry Pi Modell verwendest du?
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {PI_MODELS.map(model => (
            <button
              key={model.id}
              onClick={() => setSelectedPi(model.id)}
              className={`border-2 rounded-3xl p-4 text-left transition-all duration-200
                          hover:-translate-y-0.5 hover:shadow-lift
                          ${selectedPi === model.id
                            ? "border-honey bg-honey/8 shadow-glow-honey"
                            : "border-border bg-white shadow-card"}`}
            >
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xl">{model.emoji}</span>
                <div>
                  <p className="font-display font-bold text-ink text-sm">{model.label}</p>
                  <p className="text-xs text-muted">{model.sub}</p>
                </div>
              </div>
              <p className="text-xs text-muted">{model.ram} RAM</p>
              {selectedPi === model.id && (
                <p className="text-xs font-display font-bold text-honey mt-2">✓ Ausgewählt</p>
              )}
            </button>
          ))}
        </div>

        {/* Feature summary for selected Pi */}
        {pi && (
          <div className="mt-4 bg-white border border-border rounded-2xl p-4 shadow-card">
            <p className="text-xs font-display font-bold text-muted uppercase tracking-wider mb-3">
              {pi.label} – verfügbare Features
            </p>
            <div className="flex flex-wrap gap-2">
              {pi.features.map(f => (
                <Tag key={f} color="green">{f}</Tag>
              ))}
              {pi.limitations.map(l => (
                <Tag key={l} color="red">{l}</Tag>
              ))}
            </div>
            {pi.installNote && (
              <p className="mt-3 text-xs text-muted border-t border-border pt-3">
                💡 {pi.installNote}
              </p>
            )}
          </div>
        )}

        {!pi && (
          <div className="mt-4 bg-sand border border-dashed border-border rounded-2xl p-4 text-center">
            <p className="text-sm text-muted">
              ↑ Wähle dein Pi-Modell – die Anleitung passt sich automatisch an.
            </p>
          </div>
        )}
      </div>

      {/* ── Steps ────────────────────────────────────────────────────────── */}

      {/* Step 1 – Imager download */}
      <StepBox num="01" title="Raspberry Pi Imager herunterladen">
        <p className="text-muted text-sm leading-relaxed">
          Der Raspberry Pi Imager ist ein kostenloses Programm, das das Betriebssystem
          auf die SD-Karte überträgt. Es läuft auf Windows, macOS und Linux.
        </p>
        <a href="https://www.raspberrypi.com/software/"
           target="_blank" rel="noopener noreferrer"
           className="inline-flex items-center gap-2 bg-honey text-white font-display font-bold
                      text-sm px-5 py-2.5 rounded-xl shadow-soft hover:bg-honey/90
                      hover:-translate-y-0.5 active:scale-95 transition-all">
          Raspberry Pi Imager herunterladen ↗
        </a>
      </StepBox>

      {/* Step 2 – Flash OS */}
      <StepBox num="02" title={`Betriebssystem auf SD-Karte flashen${pi ? ` (${pi.label})` : ""}`}>
        {pi ? (
          <>
            <div className="bg-honey/8 border border-honey/20 rounded-2xl p-4 mb-2">
              <p className="text-sm font-display font-bold text-honey mb-1">
                Empfohlen für {pi.label}:
              </p>
              <p className="text-sm font-mono text-charcoal">{pi.osRecommended}</p>
              <p className="text-xs text-muted mt-2">{pi.osNote}</p>
            </div>
          </>
        ) : (
          <InfoBox icon="⚠️" title="Modell auswählen" color="honey">
            Wähle oben dein Pi-Modell – wir empfehlen die passende OS-Version automatisch.
          </InfoBox>
        )}

        <div className="space-y-4 text-sm text-muted leading-relaxed">
          <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
            <p className="font-display font-bold text-ink mb-3">So gehst du vor:</p>
            <ol className="space-y-3 list-none">
              {[
                {
                  n: "1.",
                  text: <>SD-Karte in deinen Computer einstecken (mindestens 16 GB, Class 10).</>
                },
                {
                  n: "2.",
                  text: <>Raspberry Pi Imager öffnen. Klicke auf <strong>„Raspberry Pi Device"</strong> und wähle dein Modell{pi ? ` (${pi.label})` : ""}.</>
                },
                {
                  n: "3.",
                  text: <>Klicke auf <strong>„Operating System"</strong> → <strong>„Raspberry Pi OS (other)"</strong>{pi ? ` → wähle: ${pi.osRecommended}` : " → 64-bit Lite empfohlen"}.</>
                },
                {
                  n: "4.",
                  text: <>Klicke auf <strong>„Storage"</strong> und wähle deine SD-Karte aus.</>
                },
                {
                  n: "5.",
                  text: <>Klicke auf das <strong>Zahnrad-Symbol ⚙</strong> (oder „Edit Settings") für wichtige Voreinstellungen – <em>dieser Schritt ist entscheidend!</em></>
                },
              ].map(item => (
                <li key={item.n} className="flex gap-3">
                  <span className="font-display font-black text-honey w-5 flex-shrink-0">{item.n}</span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ol>
          </div>

          {/* Advanced settings detail */}
          <Screenshot label="Imager – Erweiterte Einstellungen">
            <div className="space-y-3">
              <div className="flex items-start gap-3 pb-3 border-b border-border">
                <span className="text-base">🖥️</span>
                <div>
                  <p className="font-semibold text-ink">Hostname</p>
                  <p className="text-muted text-xs mt-0.5">Empfehlung: <code className="bg-sand px-1 rounded font-mono">wundio</code> — damit ist der Pi im Heimnetz als <code className="bg-sand px-1 rounded font-mono">wundio.local</code> erreichbar.</p>
                </div>
              </div>
              <div className="flex items-start gap-3 pb-3 border-b border-border">
                <span className="text-base">👤</span>
                <div>
                  <p className="font-semibold text-ink">Benutzername & Passwort</p>
                  <p className="text-muted text-xs mt-0.5">
                    Wähle einen Benutzernamen (z.B. <code className="bg-sand px-1 rounded font-mono">wundio</code>) und ein sicheres Passwort.
                    Notiere beides – du benötigst es für die Installation per SSH.
                    <br/><span className="text-coral font-semibold">Achtung:</span> Verwende kein einfaches Passwort wie <code className="bg-sand px-1 rounded font-mono">wundio123</code> wenn die Box später im Netzwerk erreichbar ist.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3 pb-3 border-b border-border">
                <span className="text-base">📶</span>
                <div>
                  <p className="font-semibold text-ink">WLAN einrichten (optional)</p>
                  <p className="text-muted text-xs mt-0.5">
                    Du kannst hier bereits dein Heimnetzwerk eintragen. Der Pi verbindet sich dann direkt nach dem ersten Start.
                    Alternativ richtest du das WLAN später im Wundio Web-Interface ein.
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <span className="text-base">🔑</span>
                <div>
                  <p className="font-semibold text-ink">SSH aktivieren <span className="text-honey text-xs font-display font-bold border border-honey/30 bg-honey/10 rounded-full px-2 py-0.5">Wichtig!</span></p>
                  <p className="text-muted text-xs mt-0.5">
                    SSH muss aktiviert sein, damit du dich vom Computer aus mit dem Pi verbinden kannst.
                    Wähle <strong>„Passwort-Authentifizierung"</strong>.
                    Ohne SSH kannst du Wundio nicht installieren.
                  </p>
                </div>
              </div>
            </div>
          </Screenshot>

          <p>
            Nach dem Bestätigen auf <strong>„Write"</strong> klicken.
            Das Flashen dauert je nach SD-Karte 3–10 Minuten.
          </p>
        </div>
      </StepBox>

      {/* Step 3 – First boot & SSH */}
      <StepBox num="03" title="Pi starten und verbinden">
        <div className="space-y-4 text-sm text-muted leading-relaxed">
          <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
            <ol className="space-y-3 list-none">
              {[
                { n: "1.", text: <>SD-Karte in den Raspberry Pi einlegen und Strom anschließen. Eine <strong>grüne LED</strong> zeigt an, dass er bootet.</> },
                { n: "2.", text: <>Warte ca. <strong>60–90 Sekunden</strong> bis der erste Boot abgeschlossen ist.</> },
                { n: "3.", text: <>Öffne auf deinem Computer ein Terminal: <br/><span className="text-charcoal font-medium">Windows:</span> PowerShell oder Windows Terminal (<Kbd>Win</Kbd> + <Kbd>X</Kbd> → Terminal) <br/><span className="text-charcoal font-medium">Mac:</span> Terminal App (<Kbd>⌘</Kbd> + <Kbd>Leertaste</Kbd> → „Terminal") <br/><span className="text-charcoal font-medium">Linux:</span> Strg + Alt + T</> },
                { n: "4.", text: <>Mit dem Pi verbinden – ersetze <code className="bg-sand px-1 rounded font-mono">DEIN_BENUTZERNAME</code> mit dem Namen, den du in Schritt 2 gewählt hast:</> },
              ].map(item => (
                <li key={item.n} className="flex gap-3">
                  <span className="font-display font-black text-honey w-5 flex-shrink-0">{item.n}</span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ol>
          </div>
          <Code>ssh DEIN_BENUTZERNAME@wundio.local</Code>
          <div className="bg-mint/8 border border-mint/20 rounded-2xl p-4 text-xs">
            <p className="font-display font-bold text-mint mb-1">💡 Tipp: Pi nicht gefunden?</p>
            <p>Falls <code className="bg-sand px-1 rounded font-mono">wundio.local</code> nicht funktioniert, öffne deinen Router (meist <code className="bg-sand px-1 rounded font-mono">192.168.1.1</code>) und suche dort nach dem Pi in der Geräteliste. Verbinde dich dann mit der IP-Adresse direkt:<br/>
            <code className="bg-sand px-1 rounded font-mono">ssh DEIN_BENUTZERNAME@192.168.x.x</code></p>
          </div>
          <p>
            Beim ersten Verbinden erscheint eine Sicherheitsfrage – mit <Kbd>yes</Kbd> + <Kbd>Enter</Kbd> bestätigen, dann das Passwort eingeben.
          </p>
        </div>
      </StepBox>

      {/* Step 4 – Install Wundio */}
      <StepBox num="04" title="Wundio installieren">
        <div className="space-y-4 text-sm text-muted leading-relaxed">
          <p>
            Du bist jetzt im Terminal deines Raspberry Pi. Kopiere den folgenden Befehl,
            füge ihn ein (<Kbd>Ctrl</Kbd>+<Kbd>Shift</Kbd>+<Kbd>V</Kbd> im Terminal oder Rechtsklick → Einfügen)
            und bestätige mit <Kbd>Enter</Kbd>:
          </p>
          <Code>cd; curl -fsSL https://wundio.dev/install.sh | sudo bash</Code>

          <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
            <p className="font-display font-bold text-ink mb-2">Was passiert jetzt automatisch:</p>
            <ul className="space-y-2">
              {[
                `Dein ${pi ? pi.label : "Raspberry Pi"} wird erkannt – Features werden automatisch aktiviert`,
                "SPI und I2C Schnittstellen werden für RFID-Reader und OLED-Display aktiviert",
                "Alle benötigten Programme werden installiert (dauert je nach Modell 5–15 Minuten)",
                "Spotify (librespot) wird eingerichtet",
                "Ein eigenes WLAN &ldquo;Wundio-Setup&rdquo; wird gestartet",
                "Der Pi startet automatisch neu",
              ].map(item => (
                <li key={item} className="flex gap-2 text-xs">
                  <span className="text-mint flex-shrink-0">✓</span>
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>

          {pi?.id === "pi3" && (
            <div className="bg-coral/8 border border-coral/20 rounded-2xl p-4 text-xs">
              <p className="font-display font-bold text-coral mb-1">⏱ Hinweis für {pi.label}</p>
              <p>Die Installation dauert auf dem Pi 3 länger als auf neueren Modellen – bis zu 20 Minuten sind normal. Bitte nicht unterbrechen!</p>
            </div>
          )}
          {pi?.id === "pi5" && (
            <div className="bg-sky/8 border border-sky/20 rounded-2xl p-4 text-xs">
              <p className="font-display font-bold text-sky-600 mb-1">🚀 Pi 5 – voller Funktionsumfang</p>
              <p>Nach der Grundinstallation kannst du mit <code className="bg-sand px-1 rounded font-mono">sudo bash /opt/wundio/scripts/install-ollama.sh</code> das lokale KI-Modell nachinstallieren.</p>
            </div>
          )}
        </div>
      </StepBox>

      {/* Step 5 – Connect to hotspot */}
      <StepBox num="05" title="Mit Wundio verbinden & einrichten">
        <div className="space-y-4 text-sm text-muted leading-relaxed">
          <p>Nach dem automatischen Neustart erscheint ein neues WLAN:</p>
          <Screenshot label="WLAN-Einstellungen (Handy oder Computer)">
            <div className="space-y-2">
              <div className="flex items-center justify-between p-2 bg-honey/8 rounded-xl border border-honey/20">
                <div className="flex items-center gap-2">
                  <span>📶</span>
                  <span className="font-mono font-semibold text-ink">Wundio-Setup</span>
                </div>
                <span className="text-xs text-honey font-display font-bold">Verbinden</span>
              </div>
              <div className="flex items-center justify-between p-2 rounded-xl opacity-40">
                <div className="flex items-center gap-2">
                  <span>📶</span>
                  <span className="font-mono text-muted">Mein-Heimnetz</span>
                </div>
              </div>
            </div>
          </Screenshot>
          <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
            <ol className="space-y-3 list-none">
              {[
                { n: "1.", text: <>Mit dem WLAN <code className="bg-sand px-1 rounded font-mono">Wundio-Setup</code> verbinden. Passwort: <code className="bg-sand px-1 rounded font-mono font-bold text-honey">wundio123</code></> },
                { n: "2.", text: <>Browser öffnen (Chrome, Firefox, Safari) und aufrufen: <code className="bg-sand px-1.5 rounded font-mono font-bold text-honey">http://192.168.50.1:8000</code></> },
                { n: "3.", text: <>Das Wundio Web-Interface öffnet sich. Unter <strong>Einstellungen → WLAN</strong> dein Heimnetzwerk eintragen.</> },
                { n: "4.", text: <>Wundio verbindet sich automatisch und ist danach im Heimnetz erreichbar. Den Pi jetzt wieder mit dem Heimnetz verbinden und die neue IP im Router nachschlagen.</> },
              ].map(item => (
                <li key={item.n} className="flex gap-3">
                  <span className="font-display font-black text-honey w-5 flex-shrink-0">{item.n}</span>
                  <span>{item.text}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </StepBox>

      {/* Step 6 – Setup profiles */}
      <StepBox num="06" title="Kinder-Profile & RFID einrichten">
        <div className="space-y-3 text-sm text-muted leading-relaxed">
          <p>Im Web-Interface kannst du jetzt alles nach deinen Wünschen einstellen:</p>
          <div className="grid sm:grid-cols-2 gap-3">
            {[
              { icon: "👤", title: "Kinder-Profile", desc: "Namen, Emoji-Avatar und Lieblingslautstärke für jedes Kind." },
              { icon: "⬡",  title: "RFID-Tags",      desc: "Figuren oder Karten mit Spotify-Playlists oder Kinderprofilen verknüpfen." },
              { icon: "🎵", title: "Spotify",         desc: "Wundio taucht automatisch als Gerät in deiner Spotify-App auf." },
              { icon: "⚙",  title: "Einstellungen",   desc: "Gerätename, WLAN, Lautstärke-Grenzen und mehr." },
            ].map(item => (
              <div key={item.title} className="bg-white border border-border rounded-2xl p-4 shadow-card flex gap-3">
                <span className="text-2xl flex-shrink-0">{item.icon}</span>
                <div>
                  <p className="font-display font-bold text-ink text-sm">{item.title}</p>
                  <p className="text-xs text-muted mt-0.5">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </StepBox>

      {/* Done */}
      <div className="bg-white border border-border rounded-3xl p-8 text-center shadow-lift mt-4">
        <div className="text-5xl mb-4">🎉</div>
        <h2 className="font-display font-black text-2xl text-ink mb-2">Deine Wundio Box ist bereit!</h2>
        <p className="text-muted text-sm mb-6 max-w-sm mx-auto">
          Lege eine RFID-Figur auf den Reader und die Musik startet.
          Viel Spaß beim Basteln!
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a href="/docs/hardware" className="px-5 py-2.5 rounded-xl bg-sand border border-border
                                              font-display font-bold text-sm text-charcoal
                                              hover:-translate-y-0.5 transition-all">
            Hardware-Pinout ansehen
          </a>
          <a href="/docs/faq" className="px-5 py-2.5 rounded-xl bg-sand border border-border
                                         font-display font-bold text-sm text-charcoal
                                         hover:-translate-y-0.5 transition-all">
            Probleme? → FAQ
          </a>
        </div>
      </div>

      {/* Update hint */}
      <div className="mt-8 bg-sand border border-border rounded-2xl p-5">
        <p className="text-xs font-display font-bold text-muted uppercase tracking-wider mb-2">Updates</p>
        <p className="text-xs text-muted mb-3">Wundio per SSH aktuell halten:</p>
        <Code>sudo bash /opt/wundio/scripts/update.sh</Code>
      </div>
    </div>
  );
}