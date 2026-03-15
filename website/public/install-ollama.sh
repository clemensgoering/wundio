#!/usr/bin/env bash
# Wundio – Install Ollama (Pi 5, 8GB only)
# Downloads Ollama and pulls llama3.2:3b (smallest capable model).

set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[ollama]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC}    $*"; }
warn() { echo -e "${YELLOW}[warn]${NC}  $*"; }

[[ $EUID -ne 0 ]] && echo "Run as root: sudo bash install-ollama.sh" && exit 1

# Check RAM
RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
if [[ $RAM_MB -lt 6000 ]]; then
    warn "Only ${RAM_MB}MB RAM detected. Ollama needs ≥ 6GB. Aborting."
    warn "Recommended: Raspberry Pi 5 with 8GB RAM."
    exit 1
fi
info "RAM: ${RAM_MB}MB – proceeding."

# Install Ollama
info "Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service
systemctl enable ollama
systemctl start ollama
sleep 5

# Pull model
MODEL="${OLLAMA_MODEL:-llama3.2:3b}"
info "Pulling model: $MODEL (this takes a few minutes)..."
ollama pull "$MODEL"

# Update wundio env
sed -i "s/^OLLAMA_MODEL=.*/OLLAMA_MODEL=${MODEL}/" /etc/wundio/wundio.env 2>/dev/null || \
    echo "OLLAMA_MODEL=${MODEL}" >> /etc/wundio/wundio.env

ok "Ollama ready with model: ${MODEL}"
info "Test: ollama run ${MODEL} 'Hallo Wundio'"
systemctl restart wundio-core 2>/dev/null || true
