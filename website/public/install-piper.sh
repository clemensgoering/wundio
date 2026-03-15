#!/usr/bin/env bash
# Wundio – Install Piper TTS
# Downloads the Piper binary and the default German voice.

set -euo pipefail
INSTALL_DIR="/opt/wundio"
BIN_DIR="${INSTALL_DIR}/bin"
VOICE_DIR="${INSTALL_DIR}/voices"
GREEN='\033[0;32m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[piper]${NC} $*"; }
ok()   { echo -e "${GREEN}[ok]${NC}   $*"; }

[[ $EUID -ne 0 ]] && echo "Run as root: sudo bash install-piper.sh" && exit 1

mkdir -p "$BIN_DIR" "$VOICE_DIR"

# Detect architecture
ARCH=$(uname -m)
case "$ARCH" in
    aarch64) PIPER_ARCH="aarch64" ;;
    armv7l)  PIPER_ARCH="armv7l"  ;;
    x86_64)  PIPER_ARCH="x86_64"  ;;
    *)       echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

PIPER_VERSION="2023.11.14-2"
PIPER_URL="https://github.com/rhasspy/piper/releases/download/${PIPER_VERSION}/piper_linux_${PIPER_ARCH}.tar.gz"

info "Downloading Piper ${PIPER_VERSION} for ${PIPER_ARCH}..."
curl -fsSL "$PIPER_URL" -o /tmp/piper.tar.gz
tar -xzf /tmp/piper.tar.gz -C "$BIN_DIR"
chmod +x "${BIN_DIR}/piper/piper"
ln -sf "${BIN_DIR}/piper/piper" "${BIN_DIR}/piper-bin"
rm /tmp/piper.tar.gz

# Default voice: Thorsten (German male, medium quality)
VOICE="de_DE-thorsten-medium"
VOICE_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/${VOICE}.onnx"
VOICE_JSON_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/de/de_DE/thorsten/medium/${VOICE}.onnx.json"

info "Downloading voice: ${VOICE}..."
curl -fsSL --progress-bar "$VOICE_URL"      -o "${VOICE_DIR}/${VOICE}.onnx"
curl -fsSL               "$VOICE_JSON_URL" -o "${VOICE_DIR}/${VOICE}.onnx.json"

# Install espeak-ng as fallback
apt-get install -y -qq espeak-ng

# Create wrapper script so `piper` works from PATH
cat > "${BIN_DIR}/piper" << 'EOF'
#!/usr/bin/env bash
exec "/opt/wundio/bin/piper/piper" "$@"
EOF
chmod +x "${BIN_DIR}/piper"

# Update env
sed -i "s/^TTS_VOICE=.*/TTS_VOICE=${VOICE}/" /etc/wundio/wundio.env 2>/dev/null || \
    echo "TTS_VOICE=${VOICE}" >> /etc/wundio/wundio.env

ok "Piper TTS installed. Voice: ${VOICE}"
systemctl restart wundio-core 2>/dev/null || true
