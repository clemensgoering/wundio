import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default: "Wundio – Die interaktive Box für Kinder",
    template: "%s | Wundio",
  },
  description:
    "Open-source Raspberry Pi Box für Kinder. Spotify per RFID-Figur, Spiele, Lernfunktionen und KI – selbst gebaut, kostenlos, für immer offen.",
  keywords: ["raspberry pi", "kinder musikbox", "rfid", "toniebox alternative", "open source"],
  metadataBase: new URL("https://wundio.dev"),
  openGraph: {
    title:       "Wundio – Die interaktive Box für Kinder",
    description: "Spotify per RFID, Spiele & KI – selbst gebaut auf Raspberry Pi. Kostenlos & open-source.",
    url:         "https://wundio.dev",
    siteName:    "Wundio",
    type:        "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Nunito:wght@400;500;600;700;800;900&family=DM+Sans:wght@300;400;500&family=DM+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-cream text-ink font-body antialiased">
        {children}
      </body>
    </html>
  );
}