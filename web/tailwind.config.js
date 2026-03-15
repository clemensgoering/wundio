/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink:    "#0D0B09",
        paper:  "#F5F0E8",
        amber:  "#F59C1A",
        teal:   "#0EA195",
        muted:  "#6B6358",
        surface:"rgba(245,240,232,0.04)",
        border: "rgba(245,240,232,0.08)",
      },
      fontFamily: {
        display: ["'Syne'", "sans-serif"],
        body:    ["'Plus Jakarta Sans'", "sans-serif"],
      },
    },
  },
  plugins: [],
};
