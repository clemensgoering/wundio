import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Hardware" };

const BOM = [
  { part: "Raspberry Pi 3/4/5",     qty: "1×", note: "Pi 5 für KI-Features empfohlen" },
  { part: "RFID-Reader RC522",      qty: "1×", note: "SPI-Interface, sehr verbreitet" },
  { part: "OLED Display 128×64",    qty: "1×", note: "I2C, SSD1306 (3.3V)" },
  { part: "Taster / Pushbutton",    qty: "5×", note: "Play/Pause, Next, Prev, Vol+, Vol−" },
  { part: "Speaker + USB-Audio",    qty: "1×", note: "Oder DAC HAT (z.B. HiFiBerry)" },
  { part: "SD-Karte",               qty: "1×", note: "≥ 16 GB, Class 10" },
  { part: "Netzteil / Powerbank",   qty: "1×", note: "5V 3A für Pi 4/5, 2.5A für Pi 3" },
  { part: "Jumper-Kabel",           qty: "~20×", note: "Für Prototyping auf Expansion Board" },
];

const PINS = [
  { signal: "RC522 SDA (CS)",  gpio: "BCM 8 (CE0)",  pin: "24" },
  { signal: "RC522 SCK",       gpio: "BCM 11 (SCLK)", pin: "23" },
  { signal: "RC522 MOSI",      gpio: "BCM 10 (MOSI)", pin: "19" },
  { signal: "RC522 MISO",      gpio: "BCM 9 (MISO)",  pin: "21" },
  { signal: "RC522 RST",       gpio: "BCM 25",         pin: "22" },
  { signal: "RC522 GND",       gpio: "GND",            pin: "6"  },
  { signal: "RC522 3.3V",      gpio: "3.3V",           pin: "1"  },
  { signal: "OLED SDA",        gpio: "BCM 2 (I2C SDA)","pin": "3" },
  { signal: "OLED SCL",        gpio: "BCM 3 (I2C SCL)","pin": "5" },
  { signal: "OLED GND",        gpio: "GND",            pin: "9"  },
  { signal: "OLED VCC",        gpio: "3.3V",           pin: "1"  },
  { signal: "Button Play/Pause",gpio: "BCM 17",        pin: "11" },
  { signal: "Button Next",     gpio: "BCM 27",         pin: "13" },
  { signal: "Button Prev",     gpio: "BCM 22",         pin: "15" },
  { signal: "Button Vol+",     gpio: "BCM 23",         pin: "16" },
  { signal: "Button Vol−",     gpio: "BCM 24",         pin: "18" },
];

export default function HardwarePage() {
  return (
    <>
      <Nav />
      <main className="pt-14 max-w-4xl mx-auto px-6 py-20">
        <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Hardware</p>
        <h1 className="font-display font-extrabold text-4xl mb-4">Bauteile & Pinout</h1>
        <p className="text-muted mb-16 max-w-xl">
          Alle Pins nutzen BCM-Nummerierung. Buttons schalten gegen GND (Pull-Up intern aktiv).
        </p>

        {/* BOM */}
        <h2 className="font-display font-semibold text-xl text-paper mb-6">Stückliste</h2>
        <div className="border border-border rounded-2xl overflow-hidden mb-16">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="text-left py-3 px-5 text-muted font-display font-medium">Bauteil</th>
                <th className="text-left py-3 px-4 text-muted font-display font-medium w-12">Menge</th>
                <th className="text-left py-3 px-4 text-muted font-display font-medium">Hinweis</th>
              </tr>
            </thead>
            <tbody>
              {BOM.map((row, i) => (
                <tr key={row.part} className={`border-b border-border/50 last:border-0 ${i % 2 === 0 ? "" : "bg-surface"}`}>
                  <td className="py-3 px-5 text-paper/80 font-medium">{row.part}</td>
                  <td className="py-3 px-4 text-muted">{row.qty}</td>
                  <td className="py-3 px-4 text-muted">{row.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Pinout */}
        <h2 className="font-display font-semibold text-xl text-paper mb-6">GPIO Pinout (Default)</h2>
        <p className="text-muted text-sm mb-6">
          Alle Pins können in <code className="text-teal bg-black/40 px-1 rounded">/etc/wundio/wundio.env</code> geändert werden.
        </p>
        <div className="border border-border rounded-2xl overflow-hidden">
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="border-b border-border bg-surface">
                <th className="text-left py-3 px-5 text-muted font-display font-medium not-italic">Signal</th>
                <th className="text-left py-3 px-4 text-muted font-display font-medium not-italic">GPIO (BCM)</th>
                <th className="text-left py-3 px-4 text-muted font-display font-medium not-italic">Pin #</th>
              </tr>
            </thead>
            <tbody>
              {PINS.map((row, i) => (
                <tr key={row.signal} className={`border-b border-border/50 last:border-0 ${i % 2 === 0 ? "" : "bg-surface"}`}>
                  <td className="py-2.5 px-5 text-paper/70">{row.signal}</td>
                  <td className="py-2.5 px-4 text-amber/80">{row.gpio}</td>
                  <td className="py-2.5 px-4 text-teal/70">{row.pin}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </main>
      <Footer />
    </>
  );
}
