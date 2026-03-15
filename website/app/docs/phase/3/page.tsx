import type { Metadata } from "next";
import { DocHeader, Step, CodeBlock, InfoBox } from "@/components/DocComponents";

export const metadata: Metadata = { title: "Phase 3 – KI & Sprache" };

export default function Phase3Page() {
  return (
    <div>
      <DocHeader chip="Phase 3" title="KI & Sprache"
        desc="Wake-Word-Erkennung, Sprachsteuerung via Whisper und natürliche Antworten via Piper TTS." />

      <InfoBox icon="⚠️" title="Mindestanforderung" color="coral">
        Phase 3 benötigt Raspberry Pi 4 (4 GB) oder besser. Auf Pi 3 wird Whisper nicht aktiviert.
        Whisper tiny läuft auf Pi 4, das volle Erlebnis (Ollama LLM) erst auf Pi 5.
      </InfoBox>

      <Step num="01" title="Whisper STT installieren"
            code="sudo bash /opt/wundio/scripts/install-whisper.sh">
        Das Skript installiert OpenAI Whisper im tiny-Modell (ca. 75 MB). Das Modell wird lokal
        ausgeführt – keine Daten verlassen das Netz.
      </Step>

      <Step num="02" title="Piper TTS einrichten"
            code="sudo bash /opt/wundio/scripts/install-piper.sh">
        Piper ist ein schneller lokaler Text-to-Speech-Engine. Standard-Stimme: Thorsten (Deutsch).
        Weitere Stimmen sind in der Piper-Dokumentation verfügbar.
      </Step>

      <Step num="03" title="Wake-Word aktivieren">
        In der Web-UI unter <strong>Einstellungen → KI & Sprache</strong> das Wake-Word aktivieren.
        Standard: <em>„Hey Wundio"</em>. Wundio hört danach auf Spracheingaben.
      </Step>

      <Step num="04" title="Testen">
        Sprich: <em>„Hey Wundio, spiel Kindermusik"</em> oder <em>„Hey Wundio, lauter"</em>.
        Im Log unter <code className="bg-sand px-1.5 py-0.5 rounded text-xs font-mono">journalctl -u wundio-voice -f</code> siehst du die Erkennungen live.
      </Step>

      <InfoBox icon="🤖" title="Ollama LLM (Pi 5 only)" color="mint">
        Auf Pi 5 mit 8 GB kann zusätzlich ein lokales LLM (llama3.2:3b) installiert werden.
        Wundio wird damit zum interaktiven Gesprächspartner für Kinder.
        <CodeBlock>sudo bash /opt/wundio/scripts/install-ollama.sh</CodeBlock>
      </InfoBox>
    </div>
  );
}
