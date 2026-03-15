import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import type { Metadata } from "next";

export const metadata: Metadata = { title: "Module" };

const MODULES = [
  { icon: "🎵", name: "Spotify",    phase: 1, status: "live",    desc: "librespot-basierter Spotify Connect Player." },
  { icon: "👤", name: "Multi-User", phase: 2, status: "planned", desc: "Kinder-Profile mit RFID-Login." },
  { icon: "🎙️", name: "Voice",      phase: 3, status: "planned", desc: "Whisper STT + Piper TTS Wake-Word." },
  { icon: "🤖", name: "LLM Agent",  phase: 4, status: "planned", desc: "Ollama lokal, Wundio-Charakter." },
  { icon: "🎮", name: "Games",      phase: 5, status: "planned", desc: "Audio-Quizze, Rätsel, Lerneinheiten." },
  { icon: "📷", name: "Camera",     phase: 5, status: "planned", desc: "Optionales Kamera-Modul für visuelle Interaktion." },
];

export default function ModulesPage() {
  return (
    <>
      <Nav />
      <main className="pt-14 max-w-5xl mx-auto px-6 py-20">
        <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Module</p>
        <h1 className="font-display font-extrabold text-4xl mb-4">Modulares System</h1>
        <p className="text-muted mb-16 max-w-xl">
          Wundio ist modular aufgebaut. Jedes Modul kann unabhängig installiert und
          aktualisiert werden.
        </p>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {MODULES.map((m) => (
            <div key={m.name} className="border border-border bg-surface rounded-2xl p-6
                                         hover:border-amber/20 transition-colors duration-300">
              <div className="flex items-start justify-between mb-4">
                <span className="text-3xl">{m.icon}</span>
                <span className={`text-[10px] font-display font-semibold border rounded px-1.5 py-0.5
                  ${m.status === "live"
                    ? "text-teal border-teal/30 bg-teal/10"
                    : "text-muted border-border"}`}>
                  {m.status === "live" ? "LIVE" : `Phase ${m.phase}`}
                </span>
              </div>
              <h3 className="font-display font-semibold text-paper mb-1">{m.name}</h3>
              <p className="text-sm text-muted leading-relaxed">{m.desc}</p>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </>
  );
}
