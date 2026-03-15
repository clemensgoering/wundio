# Wundio 🎵

> Open-source interaktive Box für Kinder – gebaut auf dem Raspberry Pi.
> Musik via Spotify, RFID-Figuren, Spiele, Sprache und KI. Kostenlos. Self-hosted.

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-155%20passed-brightgreen)](#)
![Pi 3+](https://img.shields.io/badge/Raspberry%20Pi-3%2F4%2F5-red)
![Phase](https://img.shields.io/badge/Phase-3%20%E2%80%93%20Voice-blue)
[![Website](https://img.shields.io/badge/Website-wundio.dev-orange)](https://wundio.dev)

---

## Installation

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
```

Läuft auf Raspberry Pi 3, 4 und 5.
Leistungsintensive Features (lokales LLM, erweiterte KI) werden automatisch
anhand des Modells aktiviert oder deaktiviert – keine manuelle Konfiguration nötig.

📖 **Ausführliche Anleitung:** [wundio.dev/docs/quickstart](https://wundio.dev/docs/quickstart)

---

## Was ist Wundio?

Wundio ist eine selbst baubare, offene Alternative zu Toniebox & Co. –
aber mit deutlich mehr Möglichkeiten:

- 🎵 **Spotify via RFID** – Figur auflegen, Musik startet
- 👤 **Multi-User** – jedes Kind hat ein eigenes Profil mit eigener Playlist und Lautstärke
- 🌐 **Web-Interface** – Einrichtung und Verwaltung über den Browser im Heimnetz
- 🎙️ **Sprachsteuerung** – Wake-Word, Whisper STT, Piper TTS (Pi 4+)
- 🤖 **Lokales LLM** – Ollama mit llama3.2:3b als interaktiver Gesprächspartner (Pi 5, 8 GB)
- 🎮 **Erweiterbar** – modulares System für Spiele, Lernfunktionen, Kamera
- 🔋 **Portabel** – Batteriebetrieb mit Powerbank möglich

---

## Repo-Struktur

```
wundio/
├── core/                  # FastAPI Backend + Hardware-Services (Python)
│   ├── api/routes/        # REST-Endpoints (users, rfid, playback, voice, wifi …)
│   ├── services/          # Hardware-Abstraktion (RFID, OLED, Buttons, Spotify)
│   │   └── ai/            # Phase 3: STT, TTS, Wake-Word, Intent, Voice-Orchestrator
│   ├── models/            # DB-Modell-Helpers
│   ├── database.py        # SQLite via SQLModel, WAL-Modus
│   ├── config.py          # Zentrale Konfiguration (pydantic-settings)
│   └── main.py            # App-Einstieg, lifespan, RFID/Button/Voice-Dispatch
│
├── web/                   # React SPA (Vite + Tailwind) – Web-Interface auf dem Pi
│   └── src/pages/         # Dashboard, Users, RFID, Playback, Settings
│
├── website/               # Next.js Doku-/Marketing-Site → wundio.dev (Vercel)
│   ├── app/docs/          # Quickstart, Hardware, FAQ, Phase 0–3
│   └── public/            # Statisch ausgelieferte Skripte (install.sh, update.sh …)
│
├── scripts/               # Shell-Skripte (Source of Truth)
│   ├── install.sh         # Haupt-Installationsskript (one-liner)
│   ├── update.sh          # Update bestehender Installationen
│   ├── setup-hotspot.sh   # WiFi-Hotspot für Ersteinrichtung
│   ├── install-whisper.sh # Whisper STT (Phase 3)
│   ├── install-piper.sh   # Piper TTS (Phase 3)
│   └── install-ollama.sh  # Ollama LLM (Phase 4, Pi 5 only)
│
├── systemd/               # systemd Service-Definitionen
└── tests/                 # pytest (Phase 0–3, 155 Tests, kein Pi nötig)
```

---

## Phase-Plan

| Phase | Status | Inhalt |
|-------|--------|--------|
| **0 – Fundament** | ✅ Abgeschlossen | Hardware-Detection, SQLite DB, RFID, OLED, Install, Hotspot |
| **1 – Musik**     | ✅ Abgeschlossen | librespot (Spotify Connect), GPIO-Buttons, Web-Interface |
| **2 – Multi-User**| ✅ Abgeschlossen | Kinder-Profile, RFID-Login, personalisierte Playlists, WiFi-API |
| **3 – Sprache**   | ✅ Abgeschlossen | Whisper STT, Piper TTS, Wake-Word, Intent-Parser, Voice-API |
| **4 – LLM-Agent** | 🔨 In Arbeit    | Ollama lokal, Wundio-Charakter, Konversation, Spiele via Sprache |
| **5 – Module**    | ⬜ Geplant      | Community-Erweiterungen, Kamera, Lern-Inhalte |

---

## Hardware (Minimum)

| Bauteil | Modell | Hinweis |
|---------|--------|---------|
| Raspberry Pi | 3B / 3B+ / 4 / 5 | Pi 5 für KI-Features empfohlen |
| RFID-Reader | RC522 | SPI-Interface |
| Display | I2C OLED 128×64 | SSD1306 kompatibel |
| Taster | 5× Pushbutton | Play/Pause, Next, Prev, Vol+, Vol− |
| Audio | USB-Soundkarte oder DAC HAT | z.B. HiFiBerry |
| SD-Karte | ≥ 16 GB Class 10 | |

📐 **Vollständiges Pinout:** [wundio.dev/docs/hardware](https://wundio.dev/docs/hardware)

---

## Dev Setup (kein Pi nötig)

```bash
git clone https://github.com/clemensgoering/wundio.git
cd wundio

# Python Backend
make install        # venv + dependencies
make run            # FastAPI auf localhost:8000 (API-Docs: /api/docs)
make test           # 155 Tests, alle ohne Hardware lauffähig

# React Web-UI
make web-install    # npm install
make web-dev        # Vite auf :5173 mit Proxy auf :8000

# Website (wundio.dev)
make website-install
make website-dev    # Next.js auf :3000
```

---

## Konfiguration

Nach der Installation liegt die Konfiguration unter `/etc/wundio/wundio.env`.
Alle GPIO-Pins, Spotify-Einstellungen und Feature-Flags können dort überschrieben werden.

```bash
# Beispiel: GPIO-Pin für Play/Pause ändern
sudo nano /etc/wundio/wundio.env
# BUTTON_PLAY_PAUSE_PIN=17  →  anpassen
sudo systemctl restart wundio-core
```

---

## Beitragen

PRs sind herzlich willkommen. Bitte zuerst ein Issue öffnen, bevor größere Änderungen
umgesetzt werden. Module können als eigenständige Verzeichnisse unter `modules/`
beigesteuert werden – das Modulkonzept wird in Phase 5 ausgebaut.

---

## Lizenz

MIT · [wundio.dev](https://wundio.dev) · [github.com/clemensgoering/wundio](https://github.com/clemensgoering/wundio)