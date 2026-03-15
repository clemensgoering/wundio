import type { Metadata } from "next";
import { Nunito, DM_Sans, DM_Mono } from "next/font/google";
import "./globals.css";

const nunito = Nunito({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800", "900"],
  variable: "--font-nunito",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500"],
  variable: "--font-dm-sans",
  display: "swap",
});

const dmMono = DM_Mono({
  subsets: ["latin"],
  weight: ["400", "500"],
  variable: "--font-dm-mono",
  display: "swap",
});

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
  twitter: {
    card: "summary_large_image",
    title: "Wundio",
    description: "Open-source interaktive Kinderbox auf Raspberry Pi",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${nunito.variable} ${dmSans.variable} ${dmMono.variable}`}>
      <body className="bg-cream text-ink font-body">
        {children}
      </body>
    </html>
  );
}
