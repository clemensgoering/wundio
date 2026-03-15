# Wundio

> Open-source interactive box for kids, built on Raspberry Pi.
> Spotify via RFID, games, voice and AI. Free. Self-hosted.

[![License: MIT](https://img.shields.io/badge/License-MIT-orange.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-155%20passed-brightgreen)](#)
[![Website](https://img.shields.io/badge/Website-wundio.dev-orange)](https://wundio.dev)

## Quick Install

```bash
curl -fsSL https://wundio.dev/install.sh | sudo bash
```

Works on Raspberry Pi 3, 4 and 5.
AI features are automatically enabled or disabled based on the model.

Full guide: [wundio.dev/docs/quickstart](https://wundio.dev/docs/quickstart)

## Repository structure

```
wundio/
├── core/                  # FastAPI backend + hardware services (Python)
│   ├── api/routes/        # REST endpoints
│   ├── services/          # Hardware abstraction (RFID, OLED, Buttons, Spotify)
│   │   └── ai/            # Phase 3: STT, TTS, Wake-Word, Intent, Voice
│   ├── models/
│   ├── database.py        # SQLite via SQLModel
│   ├── config.py          # Central config (pydantic-settings)
│   └── main.py
│
├── web/                   # React SPA (Vite + Tailwind) – served by FastAPI on the Pi
│
├── scripts/               # Shell scripts
│   ├── install.sh         # Main install (one-liner)
│   ├── uninstall.sh       # Full removal
│   ├── update.sh          # Update existing installation
│   ├── setup-hotspot.sh   # WiFi hotspot for first-run setup
│   ├── install-whisper.sh # Whisper STT (Phase 3)
│   ├── install-piper.sh   # Piper TTS (Phase 3)
│   └── install-ollama.sh  # Ollama LLM (Phase 4, Pi 5 only)
│
├── systemd/               # systemd service definitions
├── tests/                 # pytest (Phase 0-3, 155 tests, no Pi required)
└── .github/workflows/     # CI: tests, lint, script sync to wundio-website
```

> The website and documentation live in a separate repository:
> [clemensgoering/wundio-website](https://github.com/clemensgoering/wundio-website)
> Scripts in `scripts/` are synced there automatically on every push to `main`.

## Phase plan

| Phase | Status | Content |
|-------|--------|---------|
| 0 - Foundation  | Done | Hardware detection, DB, RFID, OLED, install, hotspot |
| 1 - Music       | Done | librespot (Spotify Connect), GPIO buttons, web interface |
| 2 - Multi-user  | Done | Child profiles, RFID login, personalised playlists, WiFi API |
| 3 - Voice       | Done | Whisper STT, Piper TTS, wake-word, intent parser, voice API |
| 4 - LLM Agent   | Planned | Ollama local, Wundio character, conversation |
| 5 - Modules     | Planned | Community extensions, camera, learning content |

## Hardware (minimum)

| Part | Model | Note |
|------|-------|------|
| Raspberry Pi | 3B / 4 / 5 | Pi 5 recommended for AI features |
| RFID reader | RC522 | SPI interface |
| Display | I2C OLED 128x64 | SSD1306 compatible |
| Buttons | 5x pushbutton | Play/Pause, Next, Prev, Vol+/- |
| Audio | USB soundcard or DAC HAT | |

Full pinout: [wundio.dev/docs/hardware](https://wundio.dev/docs/hardware)

## Dev setup (no Pi required)

```bash
git clone https://github.com/clemensgoering/wundio.git
cd wundio
make install    # Python venv + deps
make run        # FastAPI on localhost:8000
make test       # 155 tests, all pass without hardware
```

## Configuration

After installation, settings are in `/etc/wundio/wundio.env`.
All GPIO pins and feature flags can be overridden there.

```bash
sudo nano /etc/wundio/wundio.env
sudo systemctl restart wundio-core
```

## Contributing

PRs welcome. Open an issue first for larger changes.
Modules can be contributed as standalone directories under `modules/`.

## License

MIT