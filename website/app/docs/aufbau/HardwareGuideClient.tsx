"use client";

import { useState } from "react";
import { DocHeader, InfoBox, CodeBlock } from "@/components/DocComponents";

// ── Component registry ────────────────────────────────────────────────────────

const COMPONENTS = [
  {
    id: "rfid",
    label: "RFID Reader RC522",
    emoji: "⬡",
    desc: "Erkennt Figuren und Karten",
    required: true,
  },
  {
    id: "oled",
    label: "OLED Display 128×64",
    emoji: "🖥️",
    desc: "Zeigt IP, Status und Infos an",
    required: false,
  },
  {
    id: "buttons",
    label: "Taster (5×)",
    emoji: "🔘",
    desc: "Play/Pause, Next, Prev, Vol+/−",
    required: false,
  },
  {
    id: "speaker",
    label: "Speaker + USB-Audio",
    emoji: "🔊",
    desc: "Oder DAC HAT wie HiFiBerry",
    required: true,
  },
] as const;

type ComponentId = typeof COMPONENTS[number]["id"];

// ── Pin table data ────────────────────────────────────────────────────────────

const RFID_PINS = [
  { signal: "SDA (CS)",  gpio: "BCM 8  (CE0)", pin: "24", color: "text-honey"  },
  { signal: "SCK",       gpio: "BCM 11 (SCLK)",pin: "23", color: "text-honey"  },
  { signal: "MOSI",      gpio: "BCM 10",        pin: "19", color: "text-honey"  },
  { signal: "MISO",      gpio: "BCM 9",         pin: "21", color: "text-honey"  },
  { signal: "RST",       gpio: "BCM 25",        pin: "22", color: "text-coral"  },
  { signal: "GND",       gpio: "GND",           pin: "6",  color: "text-muted"  },
  { signal: "3.3V",      gpio: "3.3V",          pin: "1",  color: "text-red-400"},
];

const OLED_PINS = [
  { signal: "SDA", gpio: "BCM 2 (I2C)", pin: "3", color: "text-sky-500" },
  { signal: "SCL", gpio: "BCM 3 (I2C)", pin: "5", color: "text-sky-500" },
  { signal: "GND", gpio: "GND",         pin: "9", color: "text-muted"   },
  { signal: "VCC", gpio: "3.3V",        pin: "1", color: "text-red-400" },
];

const BUTTON_PINS = [
  { signal: "Play/Pause", gpio: "BCM 17", pin: "11" },
  { signal: "Next",       gpio: "BCM 27", pin: "13" },
  { signal: "Prev",       gpio: "BCM 22", pin: "15" },
  { signal: "Vol +",      gpio: "BCM 23", pin: "16" },
  { signal: "Vol −",      gpio: "BCM 24", pin: "18" },
];

// ── Small helpers ─────────────────────────────────────────────────────────────

function PinTable({ rows }: {
  rows: { signal: string; gpio: string; pin: string; color?: string }[];
}) {
  return (
    <div className="border border-border rounded-2xl overflow-hidden my-4">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="bg-sand border-b border-border">
            <th className="text-left py-2 px-4 font-display not-italic font-bold text-charcoal">Signal</th>
            <th className="text-left py-2 px-4 font-display not-italic font-bold text-charcoal">GPIO (BCM)</th>
            <th className="text-left py-2 px-3 font-display not-italic font-bold text-charcoal">Pin #</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r.signal} className={`border-b border-border/50 last:border-0 ${i%2===1?"bg-cream/40":""}`}>
              <td className="py-2 px-4 text-charcoal">{r.signal}</td>
              <td className={`py-2 px-4 ${r.color ?? "text-honey/80"}`}>{r.gpio}</td>
              <td className="py-2 px-3 text-mint/70">{r.pin}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function StepCard({ num, title, children }: {
  num: string; title: string; children: React.ReactNode;
}) {
  return (
    <div className="flex gap-4 mb-8">
      <div className="flex flex-col items-center gap-1 flex-shrink-0">
        <div className="w-9 h-9 rounded-xl bg-honey flex items-center justify-center
                        font-display font-black text-white text-sm shadow-soft">
          {num}
        </div>
        <div className="w-0.5 flex-1 bg-border min-h-4" />
      </div>
      <div className="flex-1 pb-1">
        <h3 className="font-display font-bold text-ink mb-2">{title}</h3>
        <div className="text-sm text-muted leading-relaxed space-y-3">{children}</div>
      </div>
    </div>
  );
}

function SectionHeader({ emoji, title, sub }: { emoji: string; title: string; sub: string }) {
  return (
    <div className="flex items-center gap-3 mb-5 pb-3 border-b border-border">
      <div className="w-10 h-10 rounded-2xl bg-honey/12 flex items-center justify-center text-2xl flex-shrink-0">
        {emoji}
      </div>
      <div>
        <h2 className="font-display font-bold text-xl text-ink">{title}</h2>
        <p className="text-xs text-muted">{sub}</p>
      </div>
    </div>
  );
}

function Inline({ children }: { children: string }) {
  return (
    <code className="bg-sand border border-border/60 text-honey px-1.5 py-0.5 rounded-lg font-mono text-xs">
      {children}
    </code>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function HardwareGuideClient() {
  const [selected, setSelected] = useState<Set<ComponentId>>(
    new Set(["rfid", "speaker"]) // required defaults
  );

  const toggle = (id: ComponentId) => {
    const comp = COMPONENTS.find(c => c.id === id)!;
    if (comp.required) return; // can't deselect required
    setSelected(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const has = (id: ComponentId) => selected.has(id);

  return (
    <div>
      <DocHeader
        chip="Hardware Aufbau"
        title="Deine Wundio Box aufbauen"
        desc="Wähle die Komponenten die du hast – die Anleitung passt sich automatisch an."
      />

      {/* Component selector */}
      <div className="mb-10">
        <p className="text-sm font-display font-bold text-charcoal mb-3">
          Welche Komponenten baust du ein?
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {COMPONENTS.map(comp => (
            <button
              key={comp.id}
              onClick={() => toggle(comp.id)}
              className={`border-2 rounded-3xl p-4 text-left transition-all duration-200
                          relative hover:-translate-y-0.5
                          ${has(comp.id)
                            ? "border-honey bg-honey/8 shadow-soft"
                            : "border-border bg-white shadow-card opacity-60"}
                          ${comp.required ? "cursor-default" : "cursor-pointer hover:opacity-100"}`}
            >
              {comp.required && (
                <span className="absolute top-2 right-2 text-[9px] font-display font-bold
                                 bg-honey/15 text-honey px-1.5 py-0.5 rounded-full">
                  Pflicht
                </span>
              )}
              <div className="text-2xl mb-2">{comp.emoji}</div>
              <p className="font-display font-bold text-ink text-xs leading-tight mb-1">
                {comp.label}
              </p>
              <p className="text-[11px] text-muted leading-tight">{comp.desc}</p>
              {has(comp.id) && !comp.required && (
                <div className="mt-2 text-[10px] font-display font-bold text-honey">✓ Ausgewählt</div>
              )}
            </button>
          ))}
        </div>
      </div>

      <InfoBox icon="🧪" title="Prototyping-Tipp" color="mint">
        Für den Einstieg empfehlen wir ein <strong>GPIO Expansion Board</strong> mit Jumper-Kabeln –
        kein Löten nötig. Erst wenn alles funktioniert, fest verlöten.
      </InfoBox>

      {/* ── Before you start ─────────────────────────────────────────────── */}
      <div className="mb-10">
        <SectionHeader emoji="⚡" title="Bevor du anfängst" sub="Sicherheit und Vorbereitung" />
        <div className="space-y-3 text-sm text-muted">
          <div className="bg-coral/8 border border-coral/20 rounded-2xl p-4 flex gap-3">
            <span className="text-xl flex-shrink-0">🔌</span>
            <div>
              <p className="font-display font-bold text-coral text-sm mb-1">
                Raspberry Pi immer ausschalten bevor du Kabel anschließt!
              </p>
              <p className="text-xs">Falsch angeschlossene Pins können den Pi dauerhaft beschädigen.
              Immer erst ausschalten: <Inline>sudo shutdown -h now</Inline></p>
            </div>
          </div>
          <div className="bg-white border border-border rounded-2xl p-4 flex gap-3 shadow-card">
            <span className="text-xl flex-shrink-0">📐</span>
            <div>
              <p className="font-display font-bold text-ink text-sm mb-1">GPIO-Nummerierung: BCM</p>
              <p className="text-xs">Wundio verwendet die <strong>BCM-Nummerierung</strong> (Broadcom).
              Nicht die physische Pin-Nummer. Pin 1 ist immer oben links (3.3V) wenn die USB-Ports nach unten zeigen.</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── RFID ─────────────────────────────────────────────────────────── */}
      <div className="mb-10">
        <SectionHeader emoji="⬡" title="RFID Reader RC522" sub="SPI-Interface · immer erforderlich" />

        <StepCard num="1" title="SPI aktivieren">
          <p>SPI muss auf dem Pi aktiv sein. Das erledigt das Wundio-Installationsskript automatisch.
          Zur Kontrolle:</p>
          <CodeBlock>sudo raspi-config nonint do_spi 0</CodeBlock>
          <p>Danach sollte <Inline>/dev/spidev0.0</Inline> existieren.</p>
        </StepCard>

        <StepCard num="2" title="RC522 verdrahten">
          <p>Der RC522 hat 8 Pins. Verbinde ihn wie folgt mit dem Pi:</p>
          <PinTable rows={RFID_PINS} />
          <div className="bg-honey/8 border border-honey/20 rounded-2xl p-3 text-xs">
            <strong className="text-honey">Wichtig:</strong> Der RC522 arbeitet mit <strong>3.3V</strong> –
            nicht mit 5V verbinden, das beschädigt den Reader!
          </div>
        </StepCard>

        <StepCard num="3" title="Test nach der Installation">
          <CodeBlock>sudo python3 -c "import mfrc522; print('RC522 OK')"</CodeBlock>
        </StepCard>
      </div>

      {/* ── OLED ─────────────────────────────────────────────────────────── */}
      {has("oled") && (
        <div className="mb-10">
          <SectionHeader emoji="🖥️" title="OLED Display (SSD1306, 128×64)" sub="I2C-Interface · zeigt IP, Status und Nutzerinfos" />

          <div className="bg-mint/8 border border-mint/20 rounded-2xl p-4 mb-5 text-xs">
            <p className="font-display font-bold text-mint mb-1">📡 Was das OLED direkt nach dem Start anzeigt</p>
            <ul className="space-y-1 text-muted">
              <li>• <strong>Boot-Screen</strong>: Wundio-Logo und Version</li>
              <li>• <strong>Setup-Mode</strong>: SSID und IP des Hotspots</li>
              <li>• <strong>Normal-Betrieb</strong>: IP-Adresse im Heimnetz und Status</li>
              <li>• <strong>RFID-Scan</strong>: Name des angemeldeten Kindes</li>
              <li>• <strong>Wiedergabe</strong>: Titel und Künstler</li>
            </ul>
          </div>

          <StepCard num="1" title="I2C aktivieren">
            <CodeBlock>sudo raspi-config nonint do_i2c 0</CodeBlock>
            <p>Kontrolle ob Display erkannt wird (Adresse 0x3C oder 0x3D):</p>
            <CodeBlock>sudo i2cdetect -y 1</CodeBlock>
          </StepCard>

          <StepCard num="2" title="Display verdrahten">
            <p>4-Pin I2C Verbindung – sehr einfach:</p>
            <PinTable rows={OLED_PINS} />
            <div className="bg-sky/8 border border-sky/20 rounded-2xl p-3 text-xs">
              <strong className="text-sky-600">Adresse:</strong> Die meisten SSD1306-Displays
              verwenden <Inline>0x3C</Inline>. Falls nicht gefunden: in
              <Inline>/etc/wundio/wundio.env</Inline> auf <Inline>0x3D</Inline> ändern.
            </div>
          </StepCard>

          <StepCard num="3" title="Test nach der Installation">
            <CodeBlock>sudo /opt/wundio/venv/bin/python -c "from services.display import get_display; d=get_display(); d.setup(); d.show_idle('Test!')"</CodeBlock>
          </StepCard>
        </div>
      )}

      {/* ── Buttons ──────────────────────────────────────────────────────── */}
      {has("buttons") && (
        <div className="mb-10">
          <SectionHeader emoji="🔘" title="Taster (5×)" sub="GPIO · Pull-Up intern aktiv" />

          <StepCard num="1" title="Schaltung verstehen">
            <p>Die Taster schalten gegen <strong>GND</strong>. Der interne Pull-Up des Pi hält den Pin
            auf HIGH (3.3V) solange der Taster offen ist. Beim Drücken: LOW → Aktion ausgelöst.</p>
            <div className="bg-white border border-border rounded-2xl p-3 text-xs shadow-card font-mono">
              Pi GPIO ──[Taster]── GND
            </div>
            <p className="text-xs">Kein Widerstand nötig – der Pi hat interne Pull-Up-Widerstände.</p>
          </StepCard>

          <StepCard num="2" title="Taster verdrahten">
            <PinTable rows={BUTTON_PINS.map(r => ({ ...r, color: "text-coral/80" }))} />
            <p className="text-xs">Zweites Bein jedes Tasters → beliebige GND-Pin (z.B. Pin 6, 9, 14, 20, 25).</p>
          </StepCard>

          <StepCard num="3" title="Test">
            <p>Nach der Installation im Web-Interface unter <strong>Wiedergabe → Taste simulieren</strong>
            testen, oder über die API:</p>
            <CodeBlock>curl -X POST http://wundio.local:8000/api/playback/button/play_pause</CodeBlock>
          </StepCard>
        </div>
      )}

      {/* ── Speaker ──────────────────────────────────────────────────────── */}
      {has("speaker") && (
        <div className="mb-10">
          <SectionHeader emoji="🔊" title="Audio-Ausgabe" sub="USB-Soundkarte oder DAC HAT" />

          <div className="grid sm:grid-cols-2 gap-4 mb-5">
            <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
              <p className="font-display font-bold text-ink text-sm mb-2">Option A: USB-Soundkarte</p>
              <ul className="text-xs text-muted space-y-1">
                <li>✓ Einfachste Option, ~5–15 €</li>
                <li>✓ Kein Löten, einfach einstecken</li>
                <li>✓ Genügend Qualität für Kinder</li>
                <li>→ In USB-Port stecken, fertig</li>
              </ul>
            </div>
            <div className="bg-white border border-border rounded-2xl p-4 shadow-card">
              <p className="font-display font-bold text-ink text-sm mb-2">Option B: HiFiBerry DAC+</p>
              <ul className="text-xs text-muted space-y-1">
                <li>✓ Bessere Klangqualität</li>
                <li>✓ Direkt auf GPIO-Header</li>
                <li>⚠ Belegt GPIO-Pins (kein Konflikt mit Wundio)</li>
                <li>→ Treiber-Setup nötig</li>
              </ul>
            </div>
          </div>

          <StepCard num="1" title="USB-Soundkarte einrichten">
            <p>Nach dem Einstecken prüfen ob sie erkannt wurde:</p>
            <CodeBlock>aplay -l</CodeBlock>
            <p>Standard-Soundkarte setzen (Card-Nummer anpassen – meist 1):</p>
            <CodeBlock>{"echo 'defaults.pcm.card 1\ndefaults.ctl.card 1' | sudo tee /etc/asound.conf"}</CodeBlock>
          </StepCard>

          <StepCard num="2" title="Lautstärke einstellen">
            <CodeBlock>amixer sset Master 70%</CodeBlock>
            <p>Oder im Wundio Web-Interface unter <strong>Wiedergabe → Lautstärke</strong>.</p>
          </StepCard>
        </div>
      )}

      {/* ── Full wiring summary ───────────────────────────────────────────── */}
      {selected.size > 1 && (
        <div className="mb-10">
          <SectionHeader emoji="🗺️" title="Zusammenfassung deiner Verdrahtung" sub="Alle ausgewählten Komponenten auf einen Blick" />
          <div className="bg-ink rounded-3xl p-6 text-white/80 text-xs font-mono space-y-3">
            <p className="text-honey/70 mb-3"># Raspberry Pi GPIO – Wundio Belegung</p>
            {has("rfid") && (
              <>
                <p className="text-white/40"># RC522 RFID (SPI)</p>
                {RFID_PINS.map(r => (
                  <p key={r.signal}>
                    <span className="text-honey/60">Pin {r.pin.padStart(2)}</span>
                    <span className="text-white/30"> → </span>
                    <span className="text-mint/80">RC522 {r.signal}</span>
                  </p>
                ))}
              </>
            )}
            {has("oled") && (
              <>
                <p className="text-white/40 pt-2"># OLED Display (I2C)</p>
                {OLED_PINS.map(r => (
                  <p key={r.signal}>
                    <span className="text-honey/60">Pin {r.pin.padStart(2)}</span>
                    <span className="text-white/30"> → </span>
                    <span className="text-sky-400/80">OLED {r.signal}</span>
                  </p>
                ))}
              </>
            )}
            {has("buttons") && (
              <>
                <p className="text-white/40 pt-2"># Taster (→ GND)</p>
                {BUTTON_PINS.map(r => (
                  <p key={r.signal}>
                    <span className="text-honey/60">Pin {r.pin.padStart(2)}</span>
                    <span className="text-white/30"> → </span>
                    <span className="text-coral/80">Taster {r.signal}</span>
                  </p>
                ))}
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Next step ────────────────────────────────────────────────────── */}
      <div className="bg-white border border-border rounded-3xl p-6 shadow-lift text-center">
        <div className="text-4xl mb-3">🔧</div>
        <h3 className="font-display font-black text-xl text-ink mb-2">Hardware fertig verdrahtet?</h3>
        <p className="text-muted text-sm mb-5">
          Jetzt Wundio installieren – das Skript erkennt angeschlossene Komponenten automatisch.
        </p>
        <a href="/docs/quickstart"
           className="inline-block px-7 py-3 rounded-2xl bg-honey text-white
                      font-display font-bold text-sm shadow-soft
                      hover:bg-honey/90 hover:-translate-y-0.5 active:scale-95 transition-all">
          Weiter zur Installation →
        </a>
      </div>
    </div>
  );
}