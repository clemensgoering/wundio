export const FEATURES = [
  {
    icon: "🎵",
    title: "Spotify via RFID",
    description: "Figur auf den Reader legen – Musik startet sofort. Kein Bildschirm, keine App.",
    tag: "Phase 1",
  },
  {
    icon: "👤",
    title: "Mehrere Kinder",
    description: "Jedes Kind hat ein eigenes Profil mit Playlists, Lautstärke und Favoriten.",
    tag: "Phase 2",
  },
  {
    icon: "🌐",
    title: "Web-Interface",
    description: "Alles über den Browser im Heimnetz einrichten – keine App nötig.",
    tag: "Phase 1",
  },
  {
    icon: "🤖",
    title: "KI-Interaktion",
    description: "Wundio hört zu, antwortet und wächst mit dem Kind. Lokal, ohne Cloud-Zwang.",
    tag: "Phase 4",
  },
  {
    icon: "🎮",
    title: "Spiele & Lernen",
    description: "Modulares System – Quizze, Rätsel und Lerneinheiten werden nachinstalliert.",
    tag: "Phase 5",
  },
  {
    icon: "🔋",
    title: "Batteriebetrieb",
    description: "Portabel mit Powerbank. Kein festes Setup – ideal für unterwegs.",
    tag: "Hardware",
  },
] as const;

export const COMPAT = [
  { feature: "Spotify (librespot)",     pi3: true,  pi4: true,  pi5: true  },
  { feature: "RFID RC522",              pi3: true,  pi4: true,  pi5: true  },
  { feature: "OLED Display (I2C)",      pi3: true,  pi4: true,  pi5: true  },
  { feature: "Buttons (GPIO)",          pi3: true,  pi4: true,  pi5: true  },
  { feature: "Web-Interface",           pi3: true,  pi4: true,  pi5: true  },
  { feature: "Multi-User",              pi3: true,  pi4: true,  pi5: true  },
  { feature: "Erweiterte Spiele",       pi3: false, pi4: true,  pi5: true  },
  { feature: "Cloud KI (optional)",     pi3: false, pi4: true,  pi5: true  },
  { feature: "Lokales LLM (Ollama)",    pi3: false, pi4: false, pi5: true  },
] as const;

export const PHASES = [
  { id: 0, label: "Fundament",  desc: "Hardware-Detection, DB, RFID, OLED, Install, Hotspot", done: true  },
  { id: 1, label: "Musik",      desc: "librespot, Buttons, Web-Interface",                    done: true  },
  { id: 2, label: "Multi-User", desc: "Kinder-Profile, RFID-Login, personalisiert",           done: false },
  { id: 3, label: "KI Basis",   desc: "Whisper STT, Piper TTS, Wake-Word",                    done: false },
  { id: 4, label: "LLM-Agent",  desc: "Ollama lokal, Charakter, Spiele via Sprache",          done: false },
  { id: 5, label: "Module",     desc: "Community-Erweiterungen, Kamera, Lern-Inhalte",        done: false },
] as const;
