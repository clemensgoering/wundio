export function Footer() {
  return (
    <footer className="border-t border-border mt-32 py-12">
      <div className="max-w-6xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-muted">
        <div className="flex items-center gap-2 font-display font-semibold text-paper/60">
          <span className="w-5 h-5 rounded bg-amber/20 flex items-center justify-center text-amber text-[10px] font-black">W</span>
          Wundio
        </div>
        <div className="flex gap-6">
          <a href="/docs"    className="hover:text-paper transition-colors">Docs</a>
          <a href="/modules" className="hover:text-paper transition-colors">Module</a>
          <a href="https://github.com/YOUR_ORG/wundio" target="_blank" rel="noopener noreferrer" className="hover:text-paper transition-colors">GitHub</a>
        </div>
        <p className="text-muted/60 text-xs">MIT License · Made with ♥ for our kids</p>
      </div>
    </footer>
  );
}
