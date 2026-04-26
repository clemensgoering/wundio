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

## Updates

Keep your Wundio Box up to date:

```bash
# Quick update (code from GitHub, ~10 seconds)
sudo bash /opt/wundio/scripts/wundio-pull

# Full update (code + frontend rebuild, ~5 minutes)
sudo bash /opt/wundio/scripts/wundio-pull --full

# System update (OS packages + Python libraries)
sudo bash /opt/wundio/scripts/update.sh
```

After updates:
```bash
sudo systemctl restart wundio-core
```

[Full update documentation](https://wundio.dev/docs/updates)

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
│   ├── update.sh          # System update (OS + Python libs)
│   ├── wundio-pull        # Code update from GitHub (NEW)
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

## Development

### Local Development (PC)

**Backend:**
```bash
cd core
python3 -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd web
npm install
npm run dev  # http://localhost:5173
```

### Deploy to Pi

**Option 1: Git Pull (Recommended)**
```bash
# On Pi:
sudo bash /opt/wundio/scripts/wundio-pull
sudo systemctl restart wundio-core
```

**Option 2: Direct Push from PC**
```bash
# On PC:
git push origin main

# On Pi:
cd /opt/wundio
git pull
sudo systemctl restart wundio-core
```

### Testing

```bash
# Run tests locally (no Pi required)
pytest tests/

# Run with coverage
pytest --cov=core tests/
```

## Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Website:** [wundio.dev](https://wundio.dev)
- **Documentation:** [wundio.dev/docs](https://wundio.dev/docs)
- **Hardware Guide:** [wundio.dev/docs/hardware](https://wundio.dev/docs/hardware)
- **Community:** [GitHub Discussions](https://github.com/clemensgoering/wundio/discussions)