import type { Metadata } from "next";
import { DocHeader, Step, CodeBlock, InfoBox } from "@/components/DocComponents";

export const metadata: Metadata = { title: "Quickstart" };

export default function QuickstartPage() {
  return (
    <div>
      <DocHeader
        chip="Quickstart"
        title="Von Null zur Box in 20 Min."
        desc="Raspberry Pi OS flashen, einen Befehl ausführen – fertig. Die Box konfiguriert sich danach selbst über deinen Browser."
      />

      <InfoBox icon="💡" title="Was du brauchst" color="honey">
        Raspberry Pi 3/4/5 · RFID RC522 · OLED 128×64 (I2C) · 5 Taster · Speaker · SD-Karte ≥16 GB
      </InfoBox>

      <Step num="01" title="Pi OS Bookworm installieren">
        Mit dem{" "}
        <a href="https://www.raspberrypi.com/software/" target="_blank" rel="noopener noreferrer"
           className="text-honey underline underline-offset-2">Raspberry Pi Imager</a>{" "}
        Bookworm 64-bit Lite auf die SD-Karte flashen.
        Unter „Erweiterte Optionen" Hostname, SSH und WLAN-Zugangsdaten eintragen.
      </Step>

      <Step num="02" title="Wundio installieren"
            code="cd; curl -fsSL https://wundio.dev/install.sh | sudo bash">
        Das Skript erkennt dein Pi-Modell automatisch, aktiviert SPI + I2C, richtet alle Services ein
        und startet anschließend einen WLAN-Hotspot für die Ersteinrichtung.
      </Step>

      <Step num="03" title="Mit Wundio-Setup verbinden">
        Nach dem Reboot erscheint ein WLAN namens <strong>„Wundio-Setup"</strong>.<br />
        Passwort: <code className="bg-sand px-1.5 py-0.5 rounded-lg text-honey font-mono text-xs">wundio123</code><br />
        Browser öffnen und <code className="bg-sand px-1.5 py-0.5 rounded-lg text-honey font-mono text-xs">http://192.168.50.1:8000</code> aufrufen.
      </Step>

      <Step num="04" title="Heimnetz einrichten">
        Im Web-Interface unter <strong>Einstellungen → WLAN</strong> dein Netzwerk eintragen.
        Wundio verbindet sich automatisch und ist dann über die lokale IP erreichbar.
      </Step>

      <Step num="05" title="Kinder-Profile anlegen">
        Unter <strong>Kinder</strong> neue Profile mit Emoji-Avatar und Lautstärke erstellen.
        Jedes Kind bekommt ein eigenes Profil.
      </Step>

      <Step num="06" title="RFID-Tags zuweisen">
        Unter <strong>RFID Tags</strong> Figuren oder Karten zu Playlists, Nutzerprofilen
        oder Systemaktionen zuweisen. Figur auflegen → Musik startet.
      </Step>

      <InfoBox icon="🔄" title="Updates" color="mint">
        <CodeBlock>sudo bash /opt/wundio/scripts/update.sh</CodeBlock>
      </InfoBox>
    </div>
  );
}
