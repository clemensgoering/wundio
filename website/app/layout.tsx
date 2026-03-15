import type { Metadata } from "next";
import { Syne, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const syne = Syne({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700", "800"],
  variable: "--font-syne",
  display: "swap",
});

const plusJakarta = Plus_Jakarta_Sans({
  subsets: ["latin"],
  weight: ["300", "400", "500", "600"],
  variable: "--font-plus-jakarta",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Wundio – Interactive Box for Kids",
    template: "%s | Wundio",
  },
  description:
    "Open-source Raspberry Pi box for children. Spotify, RFID, games and AI — self-hosted, free forever.",
  openGraph: {
    title:       "Wundio",
    description: "Open-source interactive box for kids",
    url:         "https://wundio.vercel.app",
    siteName:    "Wundio",
    type:        "website",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="de" className={`${syne.variable} ${plusJakarta.variable}`}>
      <body className="bg-ink text-paper font-body antialiased">
        {children}
      </body>
    </html>
  );
}
