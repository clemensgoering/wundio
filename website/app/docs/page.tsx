import type { Metadata } from "next";

export const metadata: Metadata = { title: "Dokumentation" };

const CARDS = [
  {
    icon: "🚀",
    title: "Quickstart",
    desc: "In 20 Minuten von Null zur laufenden Box.",
    href: "/docs/quickstart",
    color: "bg-honey/12 border-honey/20",
  },
  {
    icon: "🔧",
    title: "Hardware-Liste",
    desc: "Alle Bauteile, Kosten und wo man sie kauft.",
    href: "/docs/hardware",
    color: "bg-coral/12 border-coral/20",
  },
  {
    icon: "📦",
    title: "Phase 0 – Fundament",
    desc: "Installation, Hotspot-Setup und erster Start.",
    href: "/docs/phase/0",
    color: "bg-mint/12 border-mint/20",
  },
  {
    icon: "🎵",
    title: "Phase 1 – Musik",
    desc: "Spotify via librespot, Buttons, Web-Interface.",
    href: "/docs/phase/1",
    color: "bg-sky/12 border-sky/20",
  },
  {
    icon: "👤",
    title: "Phase 2 – Multi-User",
    desc: "Kinder-Profile, RFID-Login, Playlists.",
    href: "/docs/phase/2",
    color: "bg-honey/12 border-honey/20",
  },
  {
    icon: "🤖",
    title: "Phase 3 – KI & Sprache",
    desc: "Wake-Word, Whisper STT, Piper TTS.",
    href: "/docs/phase/3",
    color: "bg-coral/12 border-coral/20",
  },
  {
    icon: "❓",
    title: "FAQ",
    desc: "Häufig gestellte Fragen und Troubleshooting.",
    href: "/docs/faq",
    color: "bg-warm border-border",
  },
];

export default function DocsIndex() {
  return (
    <div>
      {/* Header */}
      <div className="mb-12">
        <span className="inline-block bg-honey/12 text-honey border border-honey/20
                         text-xs font-display font-bold uppercase tracking-widest
                         px-3.5 py-1 rounded-full mb-4">
          Dokumentation
        </span>
        <h1 className="font-display font-black text-4xl text-ink mb-3">
          Willkommen bei Wundio
        </h1>
        <p className="text-muted font-body text-lg max-w-xl leading-relaxed">
          Alles was du brauchst um deine eigene interaktive Kinderbox zu bauen –
          von der Hardware-Liste bis zur KI-Integration.
        </p>
      </div>

      {/* Cards grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {CARDS.map(card => (
          <a key={card.href} href={card.href}
             className={`group border rounded-3xl p-6 bg-white shadow-card
                         hover:-translate-y-1 hover:shadow-lift transition-all duration-200 ${card.color}`}>
            <div className="text-3xl mb-4 group-hover:scale-110 transition-transform duration-200 inline-block">
              {card.icon}
            </div>
            <h2 className="font-display font-bold text-ink mb-1.5">{card.title}</h2>
            <p className="text-sm text-muted font-body leading-relaxed">{card.desc}</p>
            <div className="mt-4 text-xs font-display font-bold text-honey group-hover:gap-2
                            flex items-center gap-1 transition-all">
              Lesen →
            </div>
          </a>
        ))}
      </div>

      {/* Quick links */}
      <div className="mt-10 bg-sand rounded-3xl p-6 border border-border">
        <p className="text-xs font-display font-bold text-muted uppercase tracking-widest mb-3">
          Schnellzugriff
        </p>
        <div className="font-mono text-sm bg-ink/90 rounded-2xl p-4 text-white/90">
          <span className="text-honey/60">$ </span>
          curl -fsSL https://wundio.dev/install.sh | sudo bash
        </div>
      </div>
    </div>
  );
}
