import { NavLink } from "react-router-dom";
import useSWR from "swr";
import { api } from "@/lib/api";
import type { SystemStatus } from "@/types/api";

const fetcher = () => api.status() as Promise<SystemStatus>;

const NAV = [
  { to: "/",         icon: "⊞", label: "Dashboard" },
  { to: "/playback", icon: "▶", label: "Wiedergabe"  },
  { to: "/users",    icon: "👤", label: "Kinder"     },
  { to: "/rfid",     icon: "⬡", label: "RFID Tags"  },
  { to: "/settings", icon: "⚙", label: "Einstellungen" },
];

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { data: status } = useSWR("status", fetcher, { refreshInterval: 10000 });

  return (
    <div className="flex min-h-screen bg-ink">
      {/* Sidebar */}
      <aside className="w-56 flex-shrink-0 border-r border-border flex flex-col">
        {/* Logo */}
        <div className="h-14 flex items-center gap-2.5 px-5 border-b border-border">
          <span className="w-7 h-7 rounded-lg bg-amber flex items-center justify-center">
            <span className="font-display font-black text-ink text-sm">W</span>
          </span>
          <span className="font-display font-bold text-paper">Wundio</span>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5">
          {NAV.map(({ to, icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all duration-150
                 ${isActive
                   ? "bg-amber/10 text-amber font-display font-semibold"
                   : "text-muted hover:text-paper hover:bg-surface"}`
              }
            >
              <span className="w-4 text-center text-base">{icon}</span>
              {label}
            </NavLink>
          ))}
        </nav>

        {/* System info */}
        {status && (
          <div className="p-3 border-t border-border">
            <div className="bg-surface rounded-xl p-3 space-y-1.5">
              <p className="text-[10px] font-display font-semibold text-muted uppercase tracking-wider">System</p>
              <p className="text-xs text-paper/60 truncate">{status.hardware.model}</p>
              <div className="flex items-center gap-1.5">
                <span className={`w-1.5 h-1.5 rounded-full ${status.setup_complete ? "bg-teal" : "bg-amber animate-pulse"}`} />
                <span className="text-xs text-muted">
                  {status.setup_complete ? "Bereit" : "Setup ausstehend"}
                </span>
              </div>
              <p className="text-[10px] text-muted/50">v{status.version}</p>
            </div>
          </div>
        )}
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        <main className="flex-1 p-8 overflow-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
