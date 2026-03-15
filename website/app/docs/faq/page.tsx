import type { Metadata } from "next";
import { DocHeader, InfoBox } from "@/components/DocComponents";

export const metadata: Metadata = { title: "FAQ" };

const FAQS = [
  {
    q: "Funktioniert Wundio ohne Internet?",
    a: "Größtenteils ja. Spotify benötigt eine aktive Internetverbindung. Das Web-Interface, RFID-Funktionen und (auf Pi 5) das lokale LLM laufen vollständig offline.",
  },
  {
    q: "Welcher Raspberry Pi ist der Mindeststandard?",
    a: "Raspberry Pi 3 Model B oder B+. Spotify, RFID, OLED und die Web-UI laufen problemlos. Für KI-Features (Whisper, Ollama) empfehlen wir Pi 5 mit 8 GB.",
  },
  {
    q: "Kann ich einen anderen RFID-Reader verwenden?",
    a: "Aktuell ist RC522 via SPI der Standard. Das Service-Interface ist abstrahiert, weitere Reader können als Modul hinzugefügt werden.",
  },
  {
    q: "Wie ändere ich die Standard-Pins?",
    a: "Alle GPIO-Pins sind in /etc/wundio/wundio.env konfigurierbar. Nach einer Änderung die Services neu starten: sudo systemctl restart wundio-core",
  },
  {
    q: "Kann ich Wundio mit Batterien betreiben?",
    a: "Ja! Eine Powerbank mit 5V 3A reicht für Pi 3/4. Für Pi 5 empfehlen wir 5V 5A oder eine spezielle Pi-5-kompatible Powerbank.",
  },
  {
    q: "Unterstützt Wundio Dienste außer Spotify?",
    a: "Aktuell ist Spotify via librespot der Standard. Das Modulsystem ist offen für weitere Audiodienste (z.B. lokale MP3-Bibliothek, Podcast-Dienste).",
  },
  {
    q: "Wie deinstalliere ich Wundio vollständig?",
    a: "sudo bash /opt/wundio/scripts/uninstall.sh – oder von überall: curl -fsSL https://wundio.dev/uninstall.sh | sudo bash. Das Skript stoppt alle Dienste, gibt Port 8000 frei, entfernt alle Dateien und den System-User. Ein abschließender Neustart wird empfohlen.",
  },
  {
    q: "Wie aktualisiere ich Wundio?",
    a: "sudo bash /opt/wundio/scripts/update.sh – das Skript hält alle Services am Laufen und startet danach neu.",
  },
  {
    q: "Wo melde ich Bugs oder schlage Features vor?",
    a: "Auf GitHub unter github.com/clemensgoering/wundio – Issues und Pull Requests sind herzlich willkommen!",
  },
];

export default function FaqPage() {
  return (
    <div>
      <DocHeader chip="FAQ" title="Häufige Fragen"
        desc="Antworten auf die häufigsten Fragen rund um Wundio." />

      <div className="space-y-4">
        {FAQS.map((faq, i) => (
          <div key={i} className="bg-white border border-border rounded-3xl p-6 shadow-card">
            <h2 className="font-display font-bold text-ink mb-2">{faq.q}</h2>
            <p className="text-muted text-sm leading-relaxed font-body">{faq.a}</p>
          </div>
        ))}
      </div>

      <InfoBox icon="💬" title="Nicht gefunden?" color="honey">
        Öffne ein{" "}
        <a href="https://github.com/clemensgoering/wundio/issues"
           target="_blank" rel="noopener noreferrer"
           className="underline underline-offset-2">GitHub Issue</a>
        {" "}– wir helfen gern.
      </InfoBox>
    </div>
  );
}