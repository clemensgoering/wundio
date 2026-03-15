import React from "react";

// ── Button ────────────────────────────────────────────────────────────────────
type BtnVariant = "primary" | "secondary" | "ghost" | "danger";

interface BtnProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: BtnVariant;
  size?: "sm" | "md";
  loading?: boolean;
}

const variantCls: Record<BtnVariant, string> = {
  primary:   "bg-amber text-ink font-semibold hover:bg-amber/90",
  secondary: "bg-surface border border-border text-paper/70 hover:border-paper/20 hover:text-paper",
  ghost:     "text-muted hover:text-paper hover:bg-surface",
  danger:    "bg-red-900/40 border border-red-700/40 text-red-400 hover:bg-red-900/60",
};

export function Button({ variant = "primary", size = "md", loading, children, className = "", disabled, ...props }: BtnProps) {
  const sz = size === "sm" ? "px-3 py-1.5 text-xs rounded-lg" : "px-4 py-2 text-sm rounded-xl";
  return (
    <button
      {...props}
      disabled={disabled || loading}
      className={`font-display inline-flex items-center gap-2 transition-all duration-200 active:scale-95
                  disabled:opacity-40 disabled:cursor-not-allowed ${variantCls[variant]} ${sz} ${className}`}
    >
      {loading && <Spinner size={14} />}
      {children}
    </button>
  );
}

// ── Card ──────────────────────────────────────────────────────────────────────
export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={`border border-border bg-surface rounded-2xl ${className}`}>
      {children}
    </div>
  );
}

// ── Badge ─────────────────────────────────────────────────────────────────────
type BadgeColor = "amber" | "teal" | "muted" | "red";
const badgeCls: Record<BadgeColor, string> = {
  amber: "text-amber border-amber/30 bg-amber/10",
  teal:  "text-teal  border-teal/30  bg-teal/10",
  muted: "text-muted border-border   bg-surface",
  red:   "text-red-400 border-red-700/30 bg-red-900/20",
};

export function Badge({ color = "muted", children }: { color?: BadgeColor; children: React.ReactNode }) {
  return (
    <span className={`text-[10px] font-display font-semibold border rounded-md px-1.5 py-0.5 ${badgeCls[color]}`}>
      {children}
    </span>
  );
}

// ── Spinner ───────────────────────────────────────────────────────────────────
export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
         className="animate-spin" style={{ minWidth: size }}>
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" strokeOpacity=".25" />
      <path d="M12 2a10 10 0 0 1 10 10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

// ── Input ─────────────────────────────────────────────────────────────────────
type InputProps = React.InputHTMLAttributes<HTMLInputElement> & { label?: string; error?: string };

export function Input({ label, error, className = "", ...props }: InputProps) {
  return (
    <label className="flex flex-col gap-1.5">
      {label && <span className="text-xs font-display font-medium text-muted">{label}</span>}
      <input
        {...props}
        className={`bg-black/30 border ${error ? "border-red-700/50" : "border-border"}
                    rounded-xl px-3 py-2 text-sm text-paper placeholder-muted/50
                    focus:outline-none focus:border-amber/40 transition-colors ${className}`}
      />
      {error && <span className="text-xs text-red-400">{error}</span>}
    </label>
  );
}

// ── Select ────────────────────────────────────────────────────────────────────
type SelectProps = React.SelectHTMLAttributes<HTMLSelectElement> & { label?: string };

export function Select({ label, children, className = "", ...props }: SelectProps) {
  return (
    <label className="flex flex-col gap-1.5">
      {label && <span className="text-xs font-display font-medium text-muted">{label}</span>}
      <select
        {...props}
        className={`bg-black/30 border border-border rounded-xl px-3 py-2 text-sm text-paper
                    focus:outline-none focus:border-amber/40 transition-colors ${className}`}
      >
        {children}
      </select>
    </label>
  );
}

// ── Modal ─────────────────────────────────────────────────────────────────────
export function Modal({ title, onClose, children }: {
  title: string; onClose: () => void; children: React.ReactNode;
}) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
         onClick={onClose}>
      <div className="w-full max-w-md bg-ink border border-border rounded-2xl shadow-2xl"
           onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between px-6 py-4 border-b border-border">
          <h2 className="font-display font-semibold text-paper">{title}</h2>
          <button onClick={onClose} className="text-muted hover:text-paper transition-colors text-lg leading-none">×</button>
        </div>
        <div className="p-6">{children}</div>
      </div>
    </div>
  );
}
