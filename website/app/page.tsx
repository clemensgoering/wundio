import { Nav } from "@/components/Nav";
import { Footer } from "@/components/Footer";
import { FEATURES, COMPAT, PHASES } from "@/lib/content";

export default function Home() {
  return (
    <>
      <Nav />

      <main className="pt-14">

        {/* ── Hero ──────────────────────────────────────────────────── */}
        <section className="relative overflow-hidden">
          {/* Background glow + dot-grid */}
          <div className="absolute inset-0 bg-radial-amber pointer-events-none" />
          <div
            className="absolute inset-0 bg-grid-dots pointer-events-none opacity-40"
            style={{ backgroundSize: "32px 32px" }}
          />

          <div className="relative max-w-5xl mx-auto px-6 pt-28 pb-24 text-center">
            {/* Badge */}
            <div className="inline-flex items-center gap-2 border border-amber/30 bg-amber/10
                            text-amber text-xs font-display font-semibold px-3 py-1 rounded-full mb-8
                            animate-fade-in animate-fill-both">
              <span className="w-1.5 h-1.5 rounded-full bg-amber animate-pulse-dim" />
              Open Source · Raspberry Pi · Kostenlos
            </div>

            {/* Headline */}
            <h1 className="font-display font-extrabold text-5xl sm:text-6xl lg:text-7xl leading-[1.05]
                           tracking-tight mb-6
                           animate-fade-up animate-fill-both animate-delay-100">
              Die Box,{" "}
              <span className="text-amber">die mit</span>
              <br />
              <span className="text-amber">deinen Kindern</span>{" "}
              wächst.
            </h1>

            <p className="text-paper/50 text-lg max-w-xl mx-auto mb-10 leading-relaxed
                          animate-fade-up animate-fill-both animate-delay-200">
              Musik von Spotify, RFID-Figuren, Spiele und KI – alles auf einem
              Raspberry Pi. Self-hosted, kostenlos, für immer open-source.
            </p>

            {/* CTAs */}
            <div className="flex flex-col sm:flex-row gap-3 justify-center
                            animate-fade-up animate-fill-both animate-delay-300">
              <a
                href="/docs/quickstart"
                className="px-6 py-3 rounded-xl bg-amber text-ink font-display font-bold
                           hover:bg-amber/90 active:scale-95 transition-all duration-200 text-sm"
              >
                Jetzt einrichten →
              </a>
              <a
                href="https://github.com/YOUR_ORG/wundio"
                target="_blank"
                rel="noopener noreferrer"
                className="px-6 py-3 rounded-xl border border-border bg-surface text-paper/70
                           font-display font-medium hover:border-paper/20 hover:text-paper
                           active:scale-95 transition-all duration-200 text-sm"
              >
                GitHub ansehen
              </a>
            </div>

            {/* Install snippet */}
            <div className="mt-10 animate-fade-up animate-fill-both animate-delay-400">
              <p className="text-xs text-muted mb-2">Ein Befehl – fertig</p>
              <div className="inline-flex items-center gap-3 bg-black/50 border border-border
                              rounded-xl px-5 py-3 font-mono text-sm text-teal">
                <span className="text-muted select-none">$</span>
                <span className="select-all">curl -fsSL https://wundio.vercel.app/install.sh | sudo bash</span>
              </div>
            </div>
          </div>
        </section>

        {/* ── Features ──────────────────────────────────────────────── */}
        <section className="max-w-6xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Features</p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl">Mehr als eine Musikbox</h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {FEATURES.map((f, i) => (
              <div
                key={f.title}
                className="group relative border border-border bg-surface rounded-2xl p-6
                           hover:border-amber/25 hover:bg-amber/5 transition-all duration-300"
              >
                {/* Phase tag */}
                <span className="absolute top-4 right-4 text-[10px] font-display font-semibold
                                 text-muted border border-border rounded-md px-1.5 py-0.5">
                  {f.tag}
                </span>
                <div className="text-3xl mb-4">{f.icon}</div>
                <h3 className="font-display font-semibold text-paper mb-2">{f.title}</h3>
                <p className="text-sm text-muted leading-relaxed">{f.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ── Roadmap ───────────────────────────────────────────────── */}
        <section className="border-y border-border py-24">
          <div className="max-w-3xl mx-auto px-6">
            <div className="text-center mb-14">
              <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Roadmap</p>
              <h2 className="font-display font-bold text-3xl sm:text-4xl">Wo wir stehen</h2>
            </div>

            <div className="space-y-0">
              {PHASES.map((phase, idx) => (
                <div key={phase.id} className="flex gap-5">
                  {/* Timeline line */}
                  <div className="flex flex-col items-center">
                    <div className={`w-8 h-8 rounded-full border-2 flex items-center justify-center flex-shrink-0 text-xs font-display font-bold
                                    ${phase.done
                                      ? "border-amber bg-amber text-ink"
                                      : "border-border bg-surface text-muted"}`}>
                      {phase.done ? "✓" : phase.id}
                    </div>
                    {idx < PHASES.length - 1 && (
                      <div className={`w-px flex-1 min-h-8 mt-1 ${phase.done ? "bg-amber/30" : "bg-border"}`} />
                    )}
                  </div>

                  {/* Content */}
                  <div className="pb-8 pt-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="font-display font-semibold text-sm text-paper">
                        Phase {phase.id} – {phase.label}
                      </span>
                      {phase.done && (
                        <span className="text-[10px] font-semibold text-amber border border-amber/30 bg-amber/10 rounded px-1.5 py-0.5">
                          LIVE
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted">{phase.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ── Compatibility ─────────────────────────────────────────── */}
        <section className="max-w-4xl mx-auto px-6 py-24">
          <div className="text-center mb-14">
            <p className="text-amber text-xs font-display font-semibold tracking-widest uppercase mb-3">Hardware</p>
            <h2 className="font-display font-bold text-3xl sm:text-4xl">Raspberry Pi Kompatibilität</h2>
            <p className="text-muted text-sm mt-3">
              Leistungsintensive Features werden automatisch deaktiviert –{" "}
              <span className="text-paper/70">keine manuelle Konfiguration nötig.</span>
            </p>
          </div>

          <div className="border border-border rounded-2xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border bg-surface">
                  <th className="text-left py-3 px-5 text-muted font-display font-medium">Feature</th>
                  {(["Pi 3", "Pi 4", "Pi 5"] as const).map(model => (
                    <th key={model} className="text-center py-3 px-4 text-muted font-display font-medium w-20">
                      {model}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {COMPAT.map((row, i) => (
                  <tr key={row.feature}
                      className={`border-b border-border/50 last:border-0 ${i % 2 === 0 ? "" : "bg-surface"}`}>
                    <td className="py-3 px-5 text-paper/70">{row.feature}</td>
                    <td className="py-3 px-4 text-center">{cell(row.pi3)}</td>
                    <td className="py-3 px-4 text-center">{cell(row.pi4)}</td>
                    <td className="py-3 px-4 text-center">{cell(row.pi5)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* ── CTA banner ────────────────────────────────────────────── */}
        <section className="max-w-6xl mx-auto px-6 pb-24">
          <div className="relative overflow-hidden rounded-3xl border border-amber/20 bg-amber/5 px-8 py-14 text-center">
            <div className="absolute inset-0 bg-radial-amber opacity-60 pointer-events-none" />
            <div className="relative">
              <h2 className="font-display font-extrabold text-3xl sm:text-4xl mb-4">
                Bereit zum Bauen?
              </h2>
              <p className="text-paper/50 mb-8 max-w-md mx-auto text-sm leading-relaxed">
                Ein Raspberry Pi, ein RFID-Reader, ein OLED-Display – und los.
                Die komplette Anleitung findest du in der Dokumentation.
              </p>
              <a
                href="/docs/quickstart"
                className="inline-block px-8 py-3.5 rounded-xl bg-amber text-ink font-display font-bold
                           hover:bg-amber/90 active:scale-95 transition-all duration-200"
              >
                Zur Anleitung →
              </a>
            </div>
          </div>
        </section>

      </main>

      <Footer />
    </>
  );
}

function cell(val: boolean) {
  return val
    ? <span className="text-teal font-semibold">✓</span>
    : <span className="text-muted/40">–</span>;
}
