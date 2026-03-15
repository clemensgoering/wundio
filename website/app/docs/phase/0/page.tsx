import type { Metadata } from "next";
import { DocHeader, InfoBox } from "@/components/DocComponents";
export const metadata: Metadata = { title: "Phase 0" };
const TITLES=["Fundament","Musik","Multi-User"];
const DESCS=["Installation, Hardware-Detection, RFID, OLED und Hotspot-Setup.","librespot Spotify-Integration, GPIO-Buttons und das Web-Interface.","Kinder-Profile, RFID-Login und personalisierte Playlists."];
export default function Page() {
  return (
    <div>
      <DocHeader chip={"Phase 0"} title={"Phase 0 – "+TITLES[0]} desc={DESCS[0]} />
      <InfoBox icon="📖" title="In Arbeit" color="honey">
        Diese Dokumentationsseite wird aktuell ausgebaut. Den vollständigen Code findest du auf{" "}
        <a href="https://github.com/clemensgoering/wundio" target="_blank" rel="noopener noreferrer"
           className="underline underline-offset-2">GitHub</a>.
      </InfoBox>
    </div>
  );
}
