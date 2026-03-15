import type { Metadata } from "next";
import { DocHeader, InfoBox, PartTable } from "@/components/DocComponents";

export const metadata: Metadata = { title: "Hardware-Liste" };

const BOM = [
  { name: "Raspberry Pi 3/4/5",  qty: "1×",  note: "Pi 5 für KI-Features empfohlen" },
  { name: "RFID-Reader RC522",   qty: "1×",  note: "SPI-Interface, ca. 3–5 €" },
  { name: "OLED 128×64 I2C",     qty: "1×",  note: "SSD1306 kompatibel, ca. 5–8 €" },
  { name: "Taster / Pushbutton", qty: "5×",  note: "Play/Pause, Next, Prev, Vol+, Vol−" },
  { name: "Speaker + USB-Audio", qty: "1×",  note: "Oder DAC HAT (z.B. HiFiBerry)" },
  { name: "SD-Karte",            qty: "1×",  note: "≥ 16 GB, Class 10 A1" },
  { name: "Netzteil / Powerbank",qty: "1×",  note: "5V 3A für Pi 4/5, 2.5A für Pi 3" },
  { name: "Jumper-Kabel",        qty: "~20×",note: "Für Prototyping auf Expansion Board" },
];

const PINS = [
  { signal: "RC522 SDA (CS)",   gpio: "BCM 8 (CE0)",   pin: "24" },
  { signal: "RC522 SCK",        gpio: "BCM 11 (SCLK)", pin: "23" },
  { signal: "RC522 MOSI",       gpio: "BCM 10 (MOSI)", pin: "19" },
  { signal: "RC522 MISO",       gpio: "BCM 9 (MISO)",  pin: "21" },
  { signal: "RC522 RST",        gpio: "BCM 25",        pin: "22" },
  { signal: "RC522 GND",        gpio: "GND",           pin: "6"  },
  { signal: "RC522 3.3V",       gpio: "3.3V",          pin: "1"  },
  { signal: "OLED SDA",         gpio: "BCM 2 (I2C)",   pin: "3"  },
  { signal: "OLED SCL",         gpio: "BCM 3 (I2C)",   pin: "5"  },
  { signal: "OLED GND",         gpio: "GND",           pin: "9"  },
  { signal: "OLED VCC",         gpio: "3.3V",          pin: "1"  },
  { signal: "Button Play/Pause",gpio: "BCM 17",        pin: "11" },
  { signal: "Button Next",      gpio: "BCM 27",        pin: "13" },
  { signal: "Button Prev",      gpio: "BCM 22",        pin: "15" },
  { signal: "Button Vol+",      gpio: "BCM 23",        pin: "16" },
  { signal: "Button Vol−",      gpio: "BCM 24",        pin: "18" },
];

export default function HardwarePage() {
  return (
    <div>
      <DocHeader chip="Hardware" title="Stückliste & Pinout"
        desc="Alle Bauteile für den Wundio-Prototypen. Pins lassen sich in /etc/wundio/wundio.env anpassen." />

      <InfoBox icon="🧪" title="Prototyping-Tipp" color="mint">
        Für erste Tests empfehlen wir ein GPIO Expansion Board mit Jumper-Kabeln statt direkt zu löten.
        So lässt sich das Setup jederzeit anpassen.
      </InfoBox>

      <h2 className="font-display font-bold text-2xl text-ink mb-4">Stückliste</h2>
      <PartTable parts={BOM} />

      <h2 className="font-display font-bold text-2xl text-ink mb-4 mt-10">GPIO Pinout (BCM)</h2>
      <div className="border border-border rounded-3xl overflow-hidden">
        <table className="w-full text-sm font-mono">
          <thead>
            <tr className="bg-sand border-b border-border">
              <th className="text-left py-3 px-5 font-display font-bold not-italic text-charcoal">Signal</th>
              <th className="text-left py-3 px-4 font-display font-bold not-italic text-charcoal">GPIO</th>
              <th className="text-left py-3 px-4 font-display font-bold not-italic text-charcoal">Pin #</th>
            </tr>
          </thead>
          <tbody>
            {PINS.map((row, i) => (
              <tr key={row.signal} className={`border-b border-border/60 last:border-0 ${i%2===1?"bg-cream/50":""}`}>
                <td className="py-2.5 px-5 text-charcoal">{row.signal}</td>
                <td className="py-2.5 px-4 text-honey/80">{row.gpio}</td>
                <td className="py-2.5 px-4 text-mint/70">{row.pin}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
