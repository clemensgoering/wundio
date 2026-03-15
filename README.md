# Wundio 🎵

> Open-source interactive box for kids – built on Raspberry Pi.
> Musik, RFID, Spiele, KI. Kostenlos. Self-hosted.

[![License: MIT](https://img.shields.io/badge/License-MIT-violet.svg)](LICENSE)
![Pi 3+](https://img.shields.io/badge/Raspberry%20Pi-3%2F4%2F5-red)
![Phase](https://img.shields.io/badge/Phase-0%20Fundament-blue)

---

## Quick Install

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
```

Läuft auf Pi 3, 4, 5. Leistungsintensive Features (Lokales LLM, erweiterte Spiele)  
werden automatisch anhand der Hardware aktiviert oder deaktiviert.

## Repo-Struktur

```
wundio/
├── core/        # FastAPI Backend + Hardware-Dienste (Python)
├── web/         # React Web-Interface (kommt in Phase 1)
├── modules/     # Optionale Erweiterungen (Phase 2+)
├── scripts/     # install.sh, update.sh, setup-hotspot.sh
├── systemd/     # Service-Definitionen
├── tests/       # pytest
└── website/     # Next.js Doku-Site → Vercel (wundio.dev)
```

## Phase-Plan

| Phase | Status | Inhalt |
|-------|--------|--------|
| 0 – Fundament | 🔨 In Progress | Hardware-Detection, DB, RFID, OLED, Install, Hotspot |
| 1 – Musik | ⬜ Planned | librespot (Spotify), Buttons, Web-UI |
| 2 – Multi-User | ⬜ Planned | Kinder-Profile, RFID-Login |
| 3 – KI Basis | ⬜ Planned | Whisper STT, Piper TTS, Wake-Word |
| 4 – LLM-Agent | ⬜ Planned | Ollama, Wundio-Charakter, Spiele via Sprache |
| 5 – Module | ⬜ Planned | Community-Module, Kamera, Lern-Inhalte |

## Hardware (Minimum)

- Raspberry Pi 3 Model B / B+
- RFID-Reader RC522 (SPI)
- I2C OLED 128×64 (SSD1306)
- 5× Taster (GPIO)
- Speaker + USB-Audio oder DAC HAT

## Dev Setup

```bash
git clone https://github.com/YOUR_ORG/wundio.git
cd wundio
make install
make run          # FastAPI auf localhost:8000
make test         # pytest (kein Pi nötig)
```

## Mitmachen

PRs willkommen. Bitte ein Issue öffnen bevor größere Änderungen.  
Module können als eigenständige Verzeichnisse unter `modules/` beigesteuert werden.

## Lizenz

MIT
