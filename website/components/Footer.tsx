export function Footer() {
  return (
    <footer className="bg-sand border-t border-border mt-24">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <div className="flex flex-col md:flex-row items-start justify-between gap-8">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-xl bg-honey flex items-center justify-center shadow-sm">
                <span className="font-display font-black text-white text-sm">W</span>
              </div>
              <span className="font-display font-black text-ink text-lg">Wundio</span>
            </div>
            <p className="text-sm text-muted max-w-xs leading-relaxed">
              Open-source interaktive Box für Kinder,<br/>gebaut mit ♥ und einem Raspberry Pi.
            </p>
          </div>

          {/* Links */}
          <div className="grid grid-cols-2 gap-x-16 gap-y-2 text-sm">
            <div className="space-y-2">
              <p className="font-display font-bold text-ink text-xs uppercase tracking-wider mb-3">Projekt</p>
              <a href="/docs"         className="block text-muted hover:text-ink transition-colors">Dokumentation</a>
              <a href="/docs/quickstart" className="block text-muted hover:text-ink transition-colors">Quickstart</a>
              <a href="/hardware"     className="block text-muted hover:text-ink transition-colors">Hardware</a>
              <a href="/modules"      className="block text-muted hover:text-ink transition-colors">Module</a>
            </div>
            <div className="space-y-2">
              <p className="font-display font-bold text-ink text-xs uppercase tracking-wider mb-3">Links</p>
              <a href="https://github.com/clemensgoering/wundio" target="_blank" rel="noopener noreferrer"
                 className="block text-muted hover:text-ink transition-colors">GitHub</a>
              <a href="/docs/faq"     className="block text-muted hover:text-ink transition-colors">FAQ</a>
            </div>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-border flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-muted">
          <span>MIT License · Wundio 2025</span>
          <span>Made with ♥ for our kids</span>
        </div>
      </div>
    </footer>
  );
}
