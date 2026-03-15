import { Nav }    from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { FEATURES, COMPAT, PHASES } from "@/lib/content";

export default function Home() {
  return (
    <>
      <Nav />
      <main className="pt-20">

        {/* ── Hero ─────────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden bg-cream">
          {/* Bg glow */}
          <div className="absolute inset-0 bg-hero-gradient pointer-events-none" />
          <div className="absolute inset-0 bg-dot-grid opacity-[0.4] pointer-events-none"
               style={{ backgroundSize: "28px 28px" }} />

          {/* Floating blobs */}
          <div className="absolute top-20 right-[8%] w-64 h-64 rounded-full
                          bg-honey/10 blur-3xl pointer-events-none animate-float" />
          <div className="absolute top-40 left-[5%] w-48 h-48 rounded-full
                          bg-coral/8 blur-3xl pointer-events-none animate-float animate-delay-300" />

          <div className="relative max-w-5xl mx-auto px-6 pt-20 pb-28 text-center">

            {/* Badge */}
            <div className="inline-flex items-center gap-2 bg-white border border-border rounded-full
                            px-4 py-1.5 mb-8 shadow-soft
                            animate-fade-in animate-fill-both">
              <span className="w-2 h-2 rounded-full bg-mint animate-pulse-soft" />
              <span className="text-xs font-display font-bold text-charcoal">
                Open Source · Kostenlos · Raspberry Pi
              </span>
            </div>

            {/* Headline */}
            <h1 className="font-display font-black text-5xl sm:text-6xl lg:text-7xl
                           leading-[1.08] tracking-tight text-ink mb-6 text-balance
                           animate-fade-up animate-fill-both animate-delay-100">
              Die Box, die mit<br />
              <span className="text-gradient-honey">deinen Kindern</span> wächst.
            </h1>

            <p className="text-charcoal/70 text-lg sm:text-xl max-w-2xl mx-auto mb-10
                          leading-relaxed font-body
                          animate-fade-up animate-fill-both animate-delay-200">
              Spotify per RFID-Figur, Spiele, Lernfunktionen und KI –
              alles auf einem Raspberry Pi. Selbst gebaut, kostenlos, für immer open-source.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center items-center
                            animate-fade-up animate-fill-both animate-delay-300">
              <a href="/docs/quickstart"
                 className="px-7 py-3.5 rounded-2xl bg-honey text-white font-display font-bold text-sm
                            shadow-soft hover:shadow-glow-honey hover:-translate-y-0.5
                            active:scale-95 transition-all duration-200">
                Jetzt einrichten ✨
              </a>
              <a href="https://github.com/clemensgoering/wundio"
                 target="_blank" rel="noopener noreferrer"
                 className="px-7 py-3.5 rounded-2xl bg-white border border-border text-charcoal
                            font-display font-bold text-sm shadow-soft
                            hover:border-charcoal/20 hover:-translate-y-0.5
                            active:scale-95 transition-all duration-200 flex items-center gap-2">
                <GithubIcon /> GitHub ansehen
              </a>
            </div>

            {/* Install snippet */}
            <div className="mt-10 animate-fade-up animate-fill-both animate-delay-400">
              <p className="text-xs text-muted mb-2 font-body">Ein Befehl – fertig</p>
              <div className="inline-flex items-center gap-3 bg-ink/90 rounded-2xl
                              px-5 py-3.5 font-mono text-sm shadow-lift">
                <span className="text-honey/60 select-none">$</span>
                <span className="text-white/90 select-all tracking-tight">
                  curl -fsSL https://wundio.dev/install.sh | sudo bash
                </span>
                <CopyHint />
              </div>
            </div>

            {/* Hero visual – emoji toy */}
            <div className="mt-16 flex justify-center gap-6 animate-fade-up animate-fill-both animate-delay-500">
              {[
                { e:"🎵", bg:"bg-honey/15",  delay:"",              label:"Musik"   },
                { e:"⬡",  bg:"bg-coral/15",  delay:"animate-delay-100", label:"RFID"    },
                { e:"🎮", bg:"bg-mint/15",   delay:"animate-delay-200", label:"Spiele"  },
                { e:"🤖", bg:"bg-sky/15",    delay:"animate-delay-300", label:"KI"      },
              ].map(item => (
                <div key={item.label}
                     className={`flex flex-col items-center gap-2 animate-float ${item.delay}`}>
                  <div className={`w-16 h-16 rounded-3xl ${item.bg} border border-white shadow-card
                                   flex items-center justify-center text-3xl
                                   hover:scale-110 transition-transform duration-200 cursor-default`}>
                    {item.e}
                  </div>
                  <span className="text-xs font-display font-bold text-muted">{item.label}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Social proof strip ─────────────────────────────────────── */}
        <section className="bg-sand border-y border-border py-5">
          <div className="max-w-5xl mx-auto px-6 flex flex-wrap justify-center gap-x-10 gap-y-2
                          text-xs font-display font-bold text-muted uppercase tracking-wider">
            {["Raspberry Pi 3/4/5","RFID RC522","I2C OLED","Spotify Connect","MIT Lizenz","Kein Abo"].map(t => (
              <span key={t} className="flex items-center gap-1.5">
                <span className="text-honey">✓</span> {t}
              </span>
            ))}
          </div>
        </section>

        {/* ── Warum Wundio ───────────────────────────────────────────── */}
        <section className="max-w-5xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <Chip>Warum Wundio?</Chip>
            <h2 className="font-display font-black text-4xl text-ink mt-4 mb-4">
              Mehr als eine Musikbox
            </h2>
            <p className="text-muted max-w-xl mx-auto text-balance">
              Bestehende Lösungen schränken ein. Wundio ist offen, erweiterbar und wächst mit deinen Kindern mit.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div key={f.title}
                   className="bg-white border border-border rounded-3xl p-6 shadow-card
                              card-hover group cursor-default">
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-3xl mb-4
                                 transition-transform duration-300 group-hover:scale-110
                                 ${FEATURE_BG[i % FEATURE_BG.length]}`}>
                  {f.icon}
                </div>
                <div className="flex items-center gap-2 mb-2">
                  <h3 className="font-display font-bold text-ink">{f.title}</h3>
                  <span className={`text-[10px] font-display font-bold px-2 py-0.5 rounded-full
                                   ${PHASE_PILL[f.tag] ?? "bg-warm text-muted"}`}>
                    {f.tag}
                  </span>
                </div>
                <p className="text-sm text-muted leading-relaxed font-body">{f.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Roadmap ────────────────────────────────────────────────── */}
        <section className="bg-sand border-y border-border py-24">
          <div className="max-w-3xl mx-auto px-6">
            <div className="text-center mb-14">
              <Chip>Roadmap</Chip>
              <h2 className="font-display font-black text-4xl text-ink mt-4">Wo wir stehen</h2>
            </div>
            <div>
              {PHASES.map((phase, idx) => (
                <div key={phase.id} className="flex gap-5">
                  <div className="flex flex-col items-center">
                    <div className={`w-10 h-10 rounded-2xl border-2 flex items-center justify-center
                                    flex-shrink-0 text-sm font-display font-black transition-all
                                    ${phase.done
                                      ? "bg-honey border-honey text-white shadow-glow-honey"
                                      : "bg-white border-border text-muted shadow-soft"}`}>
                      {phase.done ? "✓" : phase.id}
                    </div>
                    {idx < PHASES.length - 1 && (
                      <div className={`w-0.5 flex-1 min-h-8 mt-1
                                       ${phase.done ? "bg-honey/30" : "bg-border"}`} />
                    )}
                  </div>
                  <div className="pb-8 pt-1.5">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-display font-bold text-ink">
                        Phase {phase.id} – {phase.label}
                      </span>
                      {phase.done && (
                        <span className="text-[10px] font-display font-bold
                                         bg-mint/15 text-mint border border-mint/30
                                         rounded-full px-2 py-0.5">
                          LIVE ✓
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted font-body">{phase.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Compatibility ──────────────────────────────────────────── */}
        <section className="max-w-5xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <Chip>Hardware</Chip>
            <h2 className="font-display font-black text-4xl text-ink mt-4 mb-4">Welcher Pi passt?</h2>
            <p className="text-muted max-w-md mx-auto">
              Leistungsintensive Features werden automatisch an dein Modell angepasst.
            </p>
          </div>

          <div className="bg-white border border-border rounded-3xl overflow-hidden shadow-card">
            <table className="w-full text-sm font-body">
              <thead>
                <tr className="bg-sand border-b border-border">
                  <th className="text-left py-4 px-6 font-display font-bold text-charcoal">Feature</th>
                  {(["Pi 3","Pi 4","Pi 5"] as const).map(m => (
                    <th key={m} className="text-center py-4 px-5 font-display font-bold text-charcoal w-20">{m}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPAT.map((row, i) => (
                  <tr key={row.feature}
                      className={`border-b border-border last:border-0 ${i%2===1?"bg-cream/50":""}`}>
                    <td className="py-3.5 px-6 text-charcoal">{row.feature}</td>
                    <td className="py-3.5 px-5 text-center">{cell(row.pi3)}</td>
                    <td className="py-3.5 px-5 text-center">{cell(row.pi4)}</td>
                    <td className="py-3.5 px-5 text-center">{cell(row.pi5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── CTA ────────────────────────────────────────────────────── */}
        <section className="max-w-5xl mx-auto px-6 pb-28">
          <div className="relative bg-white border border-border rounded-4xl px-8 py-16
                          text-center shadow-lift overflow-hidden">
            {/* Deco blobs */}
            <div className="absolute -top-8 -right-8 w-48 h-48 rounded-full
                            bg-honey/10 blur-2xl pointer-events-none" />
            <div className="absolute -bottom-8 -left-8 w-48 h-48 rounded-full
                            bg-coral/10 blur-2xl pointer-events-none" />

            <div className="relative">
              <div className="text-5xl mb-6 animate-float">🎉</div>
              <h2 className="font-display font-black text-4xl text-ink mb-4">
                Bereit zum Bauen?
              </h2>
              <p className="text-muted mb-8 max-w-md mx-auto font-body text-balance">
                Raspberry Pi, RFID-Reader und ein OLED-Display –
                und schon kann es losgehen. Die Anleitung führt dich Schritt für Schritt.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 justify-center">
                <a href="/docs/quickstart"
                   className="px-8 py-4 rounded-2xl bg-honey text-white font-display font-bold
                              shadow-soft hover:shadow-glow-honey hover:-translate-y-0.5
                              active:scale-95 transition-all duration-200">
                  Zur Anleitung →
                </a>
                <a href="/docs"
                   className="px-8 py-4 rounded-2xl bg-sand border border-border text-charcoal
                              font-display font-bold hover:-translate-y-0.5
                              active:scale-95 transition-all duration-200">
                  Dokumentation lesen
                </a>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}

// ── Helpers ────────────────────────────────────────────────────────────────────
function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-block bg-honey/12 text-honey border border-honey/20
                     text-xs font-display font-bold uppercase tracking-widest
                     px-3.5 py-1 rounded-full">
      {children}
    </span>
  );
}

function GithubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </svg>
  );
}

function CopyHint() {
  return (
    <span className="text-white/30 text-xs font-body hidden sm:block">
      klicken zum Kopieren
    </span>
  );
}

function cell(val: boolean) {
  return val
    ? <span className="text-mint font-bold text-base">✓</span>
    : <span className="text-subtle text-base">—</span>;
}

const FEATURE_BG = [
  "bg-honey/12", "bg-coral/12", "bg-mint/12",
  "bg-sky/12",   "bg-honey/12", "bg-coral/12",
];

const PHASE_PILL: Record<string, string> = {
  "Phase 1": "bg-mint/15 text-mint",
  "Phase 2": "bg-sky/15 text-sky-600",
  "Phase 3": "bg-honey/15 text-honey",
  "Phase 4": "bg-coral/15 text-coral",
  "Phase 5": "bg-charcoal/10 text-muted",
  "Hardware": "bg-warm text-muted",
};
