import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Wundio design tokens
        ink:    "#0D0B09",
        paper:  "#F5F0E8",
        amber: {
          DEFAULT: "#F59C1A",
          dim:     "#7A4E0E",
          glow:    "rgba(245,156,26,0.15)",
        },
        teal: {
          DEFAULT: "#0EA195",
          dim:     "#054E4A",
        },
        muted:   "#6B6358",
        border:  "rgba(245,240,232,0.08)",
        surface: "rgba(245,240,232,0.04)",
      },
      fontFamily: {
        display: ["var(--font-syne)", "sans-serif"],
        body:    ["var(--font-plus-jakarta)", "sans-serif"],
      },
      backgroundImage: {
        "radial-amber": "radial-gradient(ellipse 60% 40% at 50% 0%, rgba(245,156,26,0.12) 0%, transparent 70%)",
        "grid-dots":    "radial-gradient(circle, rgba(245,240,232,0.07) 1px, transparent 1px)",
      },
      backgroundSize: {
        "grid":   "32px 32px",
      },
      animation: {
        "fade-up":   "fadeUp 0.6s ease both",
        "fade-in":   "fadeIn 0.5s ease both",
        "pulse-dim": "pulseDim 3s ease-in-out infinite",
      },
      keyframes: {
        fadeUp:   { "0%": { opacity: "0", transform: "translateY(16px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        fadeIn:   { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        pulseDim: { "0%,100%": { opacity: "0.5" }, "50%": { opacity: "1" } },
      },
    },
  },
  plugins: [],
};

export default config;
