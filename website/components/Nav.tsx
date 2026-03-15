"use client";
import { useState } from "react";

const LINKS = [
  { href: "/docs",     label: "Docs"     },
  { href: "/modules",  label: "Module"   },
  { href: "/hardware", label: "Hardware" },
];

export function Nav() {
  const [open, setOpen] = useState(false);

  return (
    <header className="fixed top-0 inset-x-0 z-50">
      <nav className="mx-4 mt-3 bg-white/80 backdrop-blur-xl border border-border rounded-2xl
                      shadow-soft px-4 h-14 flex items-center justify-between max-w-5xl lg:mx-auto">

        {/* Logo */}
        <a href="/" className="flex items-center gap-2.5 group">
          <div className="w-8 h-8 rounded-xl bg-honey flex items-center justify-center
                          shadow-sm group-hover:scale-105 transition-transform duration-200">
            <span className="font-display font-black text-white text-sm">W</span>
          </div>
          <span className="font-display font-black text-ink text-lg tracking-tight">Wundio</span>
        </a>

        {/* Desktop links */}
        <div className="hidden md:flex items-center gap-1">
          {LINKS.map(l => (
            <a key={l.href} href={l.href}
               className="px-4 py-2 rounded-xl text-sm font-body font-medium text-charcoal
                          hover:bg-sand hover:text-ink transition-all duration-150">
              {l.label}
            </a>
          ))}
          <a href="https://github.com/clemensgoering/wundio"
             target="_blank" rel="noopener noreferrer"
             className="px-4 py-2 rounded-xl text-sm font-body font-medium text-charcoal
                        hover:bg-sand hover:text-ink transition-all duration-150 flex items-center gap-1.5">
            <GithubIcon /> GitHub
          </a>
        </div>

        {/* CTA */}
        <a href="/docs/quickstart"
           className="hidden md:inline-flex items-center gap-1.5 px-4 py-2 rounded-xl
                      bg-honey text-white font-display font-bold text-sm
                      hover:bg-honey/90 active:scale-95 transition-all duration-150 shadow-sm">
          Einrichten →
        </a>

        {/* Mobile burger */}
        <button onClick={() => setOpen(!open)}
                className="md:hidden p-2 rounded-lg hover:bg-sand transition-colors">
          <span className="sr-only">Menu</span>
          <div className="space-y-1.5">
            <span className={`block w-5 h-0.5 bg-ink transition-all ${open ? "rotate-45 translate-y-2" : ""}`} />
            <span className={`block w-5 h-0.5 bg-ink transition-all ${open ? "opacity-0" : ""}`} />
            <span className={`block w-5 h-0.5 bg-ink transition-all ${open ? "-rotate-45 -translate-y-2" : ""}`} />
          </div>
        </button>
      </nav>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden mx-4 mt-2 bg-white border border-border rounded-2xl shadow-lift p-3 max-w-5xl lg:mx-auto">
          {LINKS.map(l => (
            <a key={l.href} href={l.href}
               className="block px-4 py-3 rounded-xl text-sm font-medium text-charcoal hover:bg-sand">
              {l.label}
            </a>
          ))}
          <a href="/docs/quickstart"
             className="block mt-2 px-4 py-3 rounded-xl text-sm font-bold text-center bg-honey text-white">
            Einrichten →
          </a>
        </div>
      )}
    </header>
  );
}

function GithubIcon() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
    </svg>
  );
}
