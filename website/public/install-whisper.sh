#!/usr/bin/env bash
# Wundio – Install Whisper STT
# Installs openai-whisper and downloads the tiny model.
# Pi 3: tiny only. Pi 4: tiny or base. Pi 5: up to small.

set -euo pipefail
VENV="/opt/wundio/venv"
GREEN='\033[0;32m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${BLUE}[whisper]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }

[[ $EUID -ne 0 ]] && echo "Run as root: sudo bash install-whisper.sh" && exit 1

# Detect Pi gen for model selection
MODEL="${WHISPER_MODEL:-tiny}"
RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
[[ $RAM_MB -ge 3500 ]] && MODEL="base"
[[ $RAM_MB -ge 7000 ]] && MODEL="small"
info "Selected Whisper model: $MODEL (RAM: ${RAM_MB}MB)"

# Install deps
info "Installing system dependencies..."
apt-get install -y -qq ffmpeg

# Install whisper into venv
info "Installing openai-whisper..."
"$VENV/bin/pip" install openai-whisper -q

# Pre-download model
info "Downloading Whisper '$MODEL' model..."
"$VENV/bin/python" -c "import whisper; whisper.load_model('$MODEL')"

# Update env
sed -i "s/^WHISPER_MODEL=.*/WHISPER_MODEL=${MODEL}/" /etc/wundio/wundio.env 2>/dev/null || \
    echo "WHISPER_MODEL=${MODEL}" >> /etc/wundio/wundio.env

ok "Whisper '$MODEL' installed and ready."
systemctl restart wundio-core 2>/dev/null || true
