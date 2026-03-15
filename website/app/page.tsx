import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Wundio – Interactive Box for Kids",
  description:
    "Open-source, Raspberry Pi based interactive box for children. Music, games, AI – self-hosted and free.",
  openGraph: {
    title: "Wundio",
    description: "Open-source interactive box for kids – built on Raspberry Pi",
    url: "https://wundio.dev",
  },
};

export default function Home() {
  return (
    <main className="min-h-screen bg-[#0f0f0f] text-white font-sans">

      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6 border-b border-white/10">
        <span className="text-xl font-bold tracking-tight">Wundio</span>
        <div className="flex gap-6 text-sm text-white/60">
          <a href="/docs" className="hover:text-white transition">Docs</a>
          <a href="/modules" className="hover:text-white transition">Modules</a>
          <a
            href="https://github.com/YOUR_ORG/wundio"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-white transition"
          >
            GitHub
          </a>
        </div>
      </nav>

      {/* Hero */}
      <section className="max-w-4xl mx-auto px-8 pt-28 pb-20 text-center">
        <div className="inline-block bg-white/10 text-white/70 text-xs font-medium px-3 py-1 rounded-full mb-6 border border-white/20">
          Open Source · Free · Self-Hosted
        </div>
        <h1 className="text-5xl md:text-7xl font-extrabold tracking-tight mb-6 leading-none">
          Die interaktive Box<br />
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-violet-400 to-pink-400">
            für deine Kinder.
          </span>
        </h1>
        <p className="text-lg text-white/60 max-w-xl mx-auto mb-10">
          Musik von Spotify, RFID-Figuren, Spiele und KI – alles auf einem Raspberry Pi.
          Kostenlos, open-source, leicht nachzubauen.
        </p>
        <div className="flex flex-col sm:flex-row gap-3 justify-center">
          <a
            href="/docs/quickstart"
            className="bg-violet-600 hover:bg-violet-500 text-white font-semibold px-6 py-3 rounded-xl transition"
          >
            Jetzt einrichten →
          </a>
          <a
            href="https://github.com/YOUR_ORG/wundio"
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white/10 hover:bg-white/20 text-white font-semibold px-6 py-3 rounded-xl border border-white/20 transition"
          >
            GitHub
          </a>
        </div>
      </section>

      {/* Feature Grid */}
      <section className="max-w-5xl mx-auto px-8 pb-24">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="bg-white/5 border border-white/10 rounded-2xl p-6 hover:border-white/20 transition"
            >
              <div className="text-3xl mb-3">{f.icon}</div>
              <h3 className="font-semibold text-white mb-1">{f.title}</h3>
              <p className="text-sm text-white/50">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Install snippet */}
      <section className="max-w-3xl mx-auto px-8 pb-24 text-center">
        <h2 className="text-2xl font-bold mb-4">Ein Befehl genügt</h2>
        <p className="text-white/50 text-sm mb-6">
          Funktioniert auf Raspberry Pi 3, 4 und 5. Leistungsintensive Features werden automatisch deaktiviert.
        </p>
        <div className="bg-black/60 border border-white/10 rounded-xl p-5 font-mono text-sm text-left text-violet-300 select-all">
          curl -fsSL https://wundio.dev/install.sh | sudo bash
        </div>
      </section>

      {/* Pi compat table */}
      <section className="max-w-3xl mx-auto px-8 pb-28">
        <h2 className="text-2xl font-bold text-center mb-8">Hardware-Kompatibilität</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-white/10 text-white/40 text-left">
                <th className="pb-3 pr-6">Feature</th>
                <th className="pb-3 pr-6 text-center">Pi 3</th>
                <th className="pb-3 pr-6 text-center">Pi 4</th>
                <th className="pb-3 text-center">Pi 5</th>
              </tr>
            </thead>
            <tbody>
              {COMPAT.map((row) => (
                <tr key={row.feature} className="border-b border-white/5">
                  <td className="py-3 pr-6 text-white/70">{row.feature}</td>
                  <td className="py-3 pr-6 text-center">{cell(row.pi3)}</td>
                  <td className="py-3 pr-6 text-center">{cell(row.pi4)}</td>
                  <td className="py-3 text-center">{cell(row.pi5)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 text-center text-white/30 text-sm">
        Wundio – open-source, MIT license.
        Made with ♥ for our kids.
      </footer>
    </main>
  );
}

function cell(val: boolean | "partial") {
  if (val === true) return <span className="text-green-400">✓</span>;
  if (val === "partial") return <span className="text-yellow-400">~</span>;
  return <span className="text-white/20">–</span>;
}

const FEATURES = [
  {
    icon: "🎵",
    title: "Spotify via RFID",
    description:
      "Figur auf den Reader legen → Musik startet sofort. Keine App nötig.",
  },
  {
    icon: "👤",
    title: "Mehrere Kinder",
    description:
      "Jedes Kind hat ein eigenes Profil mit personalisierten Playlists und Lautstärke.",
  },
  {
    icon: "🌐",
    title: "Web-Interface",
    description:
      "Einrichtung und Verwaltung bequem über den Browser im Heimnetz.",
  },
  {
    icon: "🤖",
    title: "KI-Interaktion",
    description:
      "Auf leistungsstarken Modellen: Wundio hört zu, antwortet und lernt. (Pi 5, opt.)",
  },
  {
    icon: "🎮",
    title: "Spiele & Lernen",
    description:
      "Modulares System – Spiele und Lerneinheiten werden einfach nachinstalliert.",
  },
  {
    icon: "🔋",
    title: "Batteriebetrieb",
    description:
      "Kein fixes Setup. Portabel mit Powerbank – ideal für unterwegs.",
  },
];

const COMPAT: {
  feature: string;
  pi3: boolean | "partial";
  pi4: boolean | "partial";
  pi5: boolean | "partial";
}[] = [
  { feature: "Spotify (librespot)",     pi3: true,      pi4: true,  pi5: true },
  { feature: "RFID RC522",              pi3: true,      pi4: true,  pi5: true },
  { feature: "OLED Display (I2C)",      pi3: true,      pi4: true,  pi5: true },
  { feature: "Buttons (GPIO)",          pi3: true,      pi4: true,  pi5: true },
  { feature: "Web-Interface",           pi3: true,      pi4: true,  pi5: true },
  { feature: "Multi-User Profile",      pi3: true,      pi4: true,  pi5: true },
  { feature: "Spiele (erweitert)",      pi3: false,     pi4: true,  pi5: true },
  { feature: "Cloud KI (opt.)",         pi3: false,     pi4: true,  pi5: true },
  { feature: "Lokales LLM (Ollama)",    pi3: false,     pi4: false, pi5: true },
];
