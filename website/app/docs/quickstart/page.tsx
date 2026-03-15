import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Quickstart" };

const STEPS = [
  {
    num: "01",
    title: "Hardware besorgen",
    content: "Raspberry Pi 3/4/5, RFID-Reader RC522, I2C OLED 128×64, 5 Taster, Speaker.",
  },
  {
    num: "02",
    title: "Pi OS Bookworm installieren",
    content: "Mit Raspberry Pi Imager Bookworm (64-bit, Lite) auf SD-Karte flashen. SSH aktivieren.",
  },
  {
    num: "03",
    title: "Wundio installieren",
    code: "cd; curl -fsSL https://wundio.vercel.app/install.sh | sudo bash",
    content: "Das Skript erkennt dein Pi-Modell automatisch und richtet alles ein.",
  },
  {
    num: "04",
    title: "Mit Wundio-Setup verbinden",
    content: "Nach dem Reboot erscheint das WLAN „Wundio-Setup". Verbinden, dann http://192.168.50.1:8000 im Browser öffnen.",
  },
  {
    num: "05",
    title: "Heimnetz einrichten",
    content: "Im Web-Interface dein WLAN eintragen. Die Box verbindet sich automatisch und ist danach über die lokale IP erreichbar.",
  },
  {
    num: "06",
    title: "RFID-Tags zuweisen",
    content: "Unter Einstellungen → RFID Figuren, Karten oder Tags zu Playlists oder Nutzerprofilen zuweisen.",
  },
];

export default function QuickstartPage() {
  return (
    <>
      <Nav />
      <main className="pt-14 max-w-3xl mx-auto px-6 py-20">
        <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Docs</p>
        <h1 className="font-display font-extrabold text-4xl mb-4">Quickstart</h1>
        <p className="text-muted mb-16">Von Null zur laufenden Wundio-Box in 20 Minuten.</p>

        <div className="space-y-12">
          {STEPS.map((step) => (
            <div key={step.num} className="flex gap-6">
              <span className="font-display font-black text-4xl text-amber/20 w-12 flex-shrink-0 leading-none">
                {step.num}
              </span>
              <div>
                <h2 className="font-display font-semibold text-lg text-paper mb-2">{step.title}</h2>
                <p className="text-muted text-sm leading-relaxed mb-3">{step.content}</p>
                {step.code && (
                  <div className="bg-black/50 border border-border rounded-lg px-4 py-3 font-mono text-sm text-teal select-all">
                    {step.code}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
