import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Light, warm, playful
        cream:   "#FFFDF8",
        sand:    "#F5EFE3",
        warm:    "#EDE4D3",
        honey:   "#F59C1A",
        coral:   "#FF6B6B",
        mint:    "#4ECDC4",
        sky:     "#74B9FF",
        ink:     "#1A1814",
        charcoal:"#3D3830",
        muted:   "#9E8E7A",
        subtle:  "#C4B8A8",
        border:  "#E8DFD0",
        card:    "#FFFFFF",
      },
      fontFamily: {
        display: ["var(--font-nunito)", "sans-serif"],
        body:    ["var(--font-dm-sans)", "sans-serif"],
        mono:    ["var(--font-dm-mono)", "monospace"],
      },
      borderRadius: {
        "4xl": "2rem",
        "5xl": "2.5rem",
      },
      boxShadow: {
        "soft":   "0 2px 16px 0 rgba(90,70,40,0.08)",
        "lift":   "0 8px 40px 0 rgba(90,70,40,0.12)",
        "card":   "0 1px 4px 0 rgba(90,70,40,0.06), 0 4px 24px 0 rgba(90,70,40,0.06)",
        "glow-honey": "0 0 40px 0 rgba(245,156,26,0.20)",
        "glow-coral": "0 0 40px 0 rgba(255,107,107,0.20)",
      },
      backgroundImage: {
        "hero-gradient":   "radial-gradient(ellipse 80% 50% at 50% -10%, rgba(245,156,26,0.15) 0%, transparent 65%)",
        "dot-grid":        "radial-gradient(circle, #C4B8A8 1px, transparent 1px)",
        "warm-gradient":   "linear-gradient(135deg, #FFFDF8 0%, #F5EFE3 100%)",
        "card-shimmer":    "linear-gradient(135deg, #FFFFFF 0%, #F7F2EA 100%)",
      },
      animation: {
        "fade-up":    "fadeUp 0.55s cubic-bezier(0.16,1,0.3,1) both",
        "fade-in":    "fadeIn 0.4s ease both",
        "float":      "float 6s ease-in-out infinite",
        "wiggle":     "wiggle 0.5s ease-in-out",
        "pop":        "pop 0.3s cubic-bezier(0.34,1.56,0.64,1) both",
        "pulse-soft": "pulseSoft 3s ease-in-out infinite",
        "slide-in":   "slideIn 0.4s cubic-bezier(0.16,1,0.3,1) both",
      },
      keyframes: {
        fadeUp:    { "0%": { opacity: "0", transform: "translateY(20px)" }, "100%": { opacity: "1", transform: "translateY(0)" } },
        fadeIn:    { "0%": { opacity: "0" }, "100%": { opacity: "1" } },
        float:     { "0%,100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-8px)" } },
        wiggle:    { "0%,100%": { transform: "rotate(0deg)" }, "25%": { transform: "rotate(-6deg)" }, "75%": { transform: "rotate(6deg)" } },
        pop:       { "0%": { opacity: "0", transform: "scale(0.8)" }, "100%": { opacity: "1", transform: "scale(1)" } },
        pulseSoft: { "0%,100%": { opacity: "0.6" }, "50%": { opacity: "1" } },
        slideIn:   { "0%": { opacity: "0", transform: "translateX(-12px)" }, "100%": { opacity: "1", transform: "translateX(0)" } },
      },
    },
  },
  plugins: [],
};

export default config;
