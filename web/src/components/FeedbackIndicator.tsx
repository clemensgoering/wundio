import { useEffect, useRef, useState } from "react";

interface FeedbackEvent {
  type:        string;
  label:       string;
  color:       string;
  duration_ms: number;
  data?:       Record<string, unknown>;
}

// Color → Tailwind classes
const COLOR_MAP: Record<string, { ring: string; bg: string; text: string; glow: string }> = {
  amber: {
    ring: "border-amber",
    bg:   "bg-amber/10",
    text: "text-amber",
    glow: "shadow-[0_0_20px_rgba(245,156,26,0.4)]",
  },
  teal: {
    ring: "border-teal",
    bg:   "bg-teal/10",
    text: "text-teal",
    glow: "shadow-[0_0_20px_rgba(14,161,149,0.4)]",
  },
  red: {
    ring: "border-red-500",
    bg:   "bg-red-500/10",
    text: "text-red-400",
    glow: "shadow-[0_0_20px_rgba(239,68,68,0.4)]",
  },
  blue: {
    ring: "border-sky-400",
    bg:   "bg-sky-400/10",
    text: "text-sky-400",
    glow: "shadow-[0_0_20px_rgba(56,189,248,0.3)]",
  },
  white: {
    ring: "border-paper/40",
    bg:   "bg-paper/5",
    text: "text-paper/60",
    glow: "shadow-[0_0_20px_rgba(245,240,232,0.2)]",
  },
};

const EVENT_ICONS: Record<string, string> = {
  rfid_scan:      "📡",
  rfid_unknown:   "❓",
  playback_start: "▶",
  playback_pause: "⏸",
  playback_stop:  "⏹",
  volume_change:  "🔊",
  track_next:     "⏭",
  track_prev:     "⏮",
  user_login:     "👋",
  system_ready:   "✓",
  error:          "⚠",
};

export default function FeedbackIndicator() {
  const [event, setEvent]   = useState<FeedbackEvent | null>(null);
  const [visible, setVisible] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const esRef    = useRef<EventSource | null>(null);

  useEffect(() => {
    const connect = () => {
      const es = new EventSource("/api/feedback/stream");
      esRef.current = es;

      es.addEventListener("feedback", (e) => {
        try {
          const ev: FeedbackEvent = JSON.parse(e.data);
          if (timerRef.current) clearTimeout(timerRef.current);

          setEvent(ev);
          setVisible(true);

          timerRef.current = setTimeout(() => {
            setVisible(false);
          }, ev.duration_ms + 600); // fade out after duration + transition time
        } catch {
          /* ignore parse errors */
        }
      });

      es.onerror = () => {
        es.close();
        // Reconnect after 3s
        setTimeout(connect, 3000);
      };
    };

    connect();
    return () => {
      esRef.current?.close();
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const colors = COLOR_MAP[event?.color ?? "amber"] ?? COLOR_MAP.amber;
  const icon   = EVENT_ICONS[event?.type ?? ""] ?? "●";

  return (
    <div
      className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50
                  transition-all duration-500 ease-out pointer-events-none
                  ${visible
                    ? "opacity-100 translate-y-0 scale-100"
                    : "opacity-0 translate-y-4 scale-95"}`}
    >
      <div
        className={`flex items-center gap-3 px-5 py-3 rounded-2xl border
                    backdrop-blur-sm ${colors.ring} ${colors.bg} ${colors.glow}
                    transition-all duration-300`}
      >
        {/* Animated pulse ring */}
        <div className="relative flex-shrink-0">
          <span className={`absolute inset-0 rounded-full ${colors.ring.replace("border-", "bg-").split(" ")[0]}
                            opacity-30 animate-ping`} />
          <span className={`relative text-base ${colors.text}`}>{icon}</span>
        </div>

        {/* Label */}
        <span className={`text-sm font-display font-semibold whitespace-nowrap ${colors.text}`}>
          {event?.label || "…"}
        </span>
      </div>
    </div>
  );
}