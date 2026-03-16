#!/usr/bin/env bash
# Wundio - Installation Script
# Usage: curl -fsSL https://wundio.dev/install.sh | sudo bash
# Or:   sudo bash scripts/install.sh

set -euo pipefail

# -- Config
GIT_URL="${WUNDIO_GIT_URL:-https://github.com/clemensgoering/wundio.git}"
GIT_BRANCH="${WUNDIO_BRANCH:-main}"
INSTALL_DIR="/opt/wundio"
DATA_DIR="/var/lib/wundio"
CONF_DIR="/etc/wundio"
VENV_DIR="${INSTALL_DIR}/venv"
WUNDIO_USER="wundio"
LOG_FILE="/var/log/wundio-install.log"

# -- Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERR ]${NC}  $*" | tee -a "$LOG_FILE"; exit 1; }
section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BOLD}-- $* --${NC}" | tee -a "$LOG_FILE"
}

# -- Spinner
_spin_frames=("." "o" "O" "o")
spin_bg() {
    local label="$1"
    local i=0
    while true; do
        printf "\r  ${CYAN}${_spin_frames[$i]}${NC}  %s..." "$label" >&2
        i=$(( (i+1) % ${#_spin_frames[@]} ))
        sleep 0.12
    done
}

run_spin() {
    local label="$1"; shift
    spin_bg "$label" &
    local SPIN_PID=$!
    set +e
    "$@" >> "$LOG_FILE" 2>&1
    local EXIT_CODE=$?
    set -e
    kill $SPIN_PID 2>/dev/null; wait $SPIN_PID 2>/dev/null || true
    printf "\r  %-60s\n" "" >&2
    if [[ $EXIT_CODE -eq 0 ]]; then
        ok "$label"
    else
        error "$label failed (exit $EXIT_CODE) - see $LOG_FILE"
    fi
    return $EXIT_CODE
}

# -- Root check
[[ $EUID -ne 0 ]] && error "Please run as root: sudo bash install.sh"

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== Wundio install $(date) ===" >> "$LOG_FILE"

# -- Banner
echo -e "${BOLD}"
cat << 'EOF'
 __        __              _ _
 \ \      / /   _ _ __   __| (_) ___
  \ \ /\ / / | | | '_ \ / _` | |/ _ \
   \ V  V /| |_| | | | | (_| | | (_) |
    \_/\_/  \__,_|_| |_|\__,_|_|\___/

  Interactive Box for Kids - wundio.dev
EOF
echo -e "${NC}"

# -- 1/10 Hardware Detection
section "1/10 Detecting hardware"

MODEL_FILE="/proc/device-tree/model"
if [[ -f "$MODEL_FILE" ]]; then
    HW_MODEL=$(tr -d '\0' < "$MODEL_FILE")
    info "Model: $HW_MODEL"
else
    HW_MODEL="unknown"
    warn "Could not detect Pi model - assuming Pi 3 (minimal features)"
fi

RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
info "RAM: ${RAM_MB} MB"

PI_GEN=0
if [[ "$HW_MODEL" =~ "Raspberry Pi 5" ]];       then PI_GEN=5
elif [[ "$HW_MODEL" =~ "Raspberry Pi 4" ]];     then PI_GEN=4
elif [[ "$HW_MODEL" =~ "Raspberry Pi 3" ]];     then PI_GEN=3
elif [[ "$HW_MODEL" =~ "Raspberry Pi Zero 2" ]]; then PI_GEN=3
elif [[ "$HW_MODEL" =~ "Raspberry Pi 2" ]];     then PI_GEN=2
else PI_GEN=3; fi

info "Pi generation: ${PI_GEN}"

FEAT_SPOTIFY=true; FEAT_RFID=true; FEAT_DISPLAY_OLED=true; FEAT_BUTTONS=true
FEAT_AI_LOCAL=false; FEAT_AI_CLOUD=false; FEAT_GAMES_ADVANCED=false
[[ $PI_GEN -ge 4 ]] && FEAT_AI_CLOUD=true && FEAT_GAMES_ADVANCED=true
[[ $PI_GEN -ge 5 && $RAM_MB -ge 7000 ]] && FEAT_AI_LOCAL=true

case $PI_GEN in
    3) EST="20-35 min" ;;
    4) EST="10-20 min" ;;
    5) EST="6-12 min"  ;;
    *) EST="10-20 min" ;;
esac
echo ""
echo -e "  ${YELLOW}Estimated installation time on Pi ${PI_GEN}: ${EST}${NC}"
echo ""
ok "Hardware detected - Pi ${PI_GEN}, ${RAM_MB} MB RAM"

# -- 1b/10 Interactive Setup Questions
# These questions run once during installation and save time later.
# All settings can be changed afterwards in the Wundio web interface.
section "1b/10 Setup questions (hardware)"

echo ""
echo -e "  ${BOLD}Welches Display ist angeschlossen?${NC}"
echo ""
echo "    0) Kein Display"
echo "    1) OLED 128x64  – SSD1306  (I2C)   ← Standard / Starter"
echo "    2) OLED 128x64  – SH1106   (I2C)"
echo "    3) TFT  128x160 – ST7735   (SPI)   ← Starter mit Farbe"
echo "    4) TFT  240x320 – ILI9341  (SPI)   ← Full-Stack"
echo ""
echo -e "  ${YELLOW}Kann jederzeit in der App unter Einstellungen > Display geändert werden.${NC}"
echo ""

SETUP_DISPLAY_TYPE="none"
SETUP_DISPLAY_MODEL="ssd1306"
SETUP_DISPLAY_WIDTH=128
SETUP_DISPLAY_HEIGHT=64
SETUP_INSTALL_LUMA_LCD=false

while true; do
    read -r -p "  Deine Wahl [0-4]: " DISPLAY_CHOICE
    case "$DISPLAY_CHOICE" in
        0)
            SETUP_DISPLAY_TYPE="none"
            ok "Kein Display - OLED/TFT deaktiviert"
            break ;;
        1)
            SETUP_DISPLAY_TYPE="oled"; SETUP_DISPLAY_MODEL="ssd1306"
            SETUP_DISPLAY_WIDTH=128;   SETUP_DISPLAY_HEIGHT=64
            ok "OLED SSD1306 (I2C 0x3C, 128x64)"
            break ;;
        2)
            SETUP_DISPLAY_TYPE="oled"; SETUP_DISPLAY_MODEL="sh1106"
            SETUP_DISPLAY_WIDTH=128;   SETUP_DISPLAY_HEIGHT=64
            ok "OLED SH1106 (I2C 0x3C, 128x64)"
            break ;;
        3)
            SETUP_DISPLAY_TYPE="tft";  SETUP_DISPLAY_MODEL="st7735"
            SETUP_DISPLAY_WIDTH=128;   SETUP_DISPLAY_HEIGHT=160
            SETUP_INSTALL_LUMA_LCD=true
            ok "TFT ST7735 (SPI CE1, 128x160)"
            break ;;
        4)
            SETUP_DISPLAY_TYPE="tft";  SETUP_DISPLAY_MODEL="ili9341"
            SETUP_DISPLAY_WIDTH=240;   SETUP_DISPLAY_HEIGHT=320
            SETUP_INSTALL_LUMA_LCD=true
            ok "TFT ILI9341 (SPI CE1, 240x320)"
            break ;;
        *)
            echo -e "  ${RED}Ungültige Eingabe. Bitte 0-4 eingeben.${NC}" ;;
    esac
done

# -- RFID-Reader
echo ""
echo -e "  ${BOLD}Welchen RFID-Reader verwendest du?${NC}"
echo ""
echo "    1) RC522  (SPI, CE0)   ← Standard / wird aktiv getestet"
echo "    2) PN532  (I2C)        ← Wundio HAT / stabiler, NFC-kompatibel"
echo ""
echo -e "  ${YELLOW}Kann jederzeit in der App unter Einstellungen > Hardware geändert werden.${NC}"
echo ""

SETUP_RFID_TYPE="rc522"
SETUP_INSTALL_PN532=false

while true; do
    read -r -p "  Deine Wahl [1-2]: " RFID_CHOICE
    case "$RFID_CHOICE" in
        1)
            SETUP_RFID_TYPE="rc522"
            ok "RFID RC522 (SPI CE0, RST BCM25)"
            break ;;
        2)
            SETUP_RFID_TYPE="pn532"
            SETUP_INSTALL_PN532=true
            ok "RFID PN532 (I2C, teilt Bus mit OLED/Display)"
            break ;;
        *)
            echo -e "  ${RED}Ungültige Eingabe. Bitte 1 oder 2 eingeben.${NC}" ;;
    esac
done

# -- Audio
echo ""
echo -e "  ${BOLD}Welche Audio-Ausgabe verwendest du?${NC}"
echo ""
echo "    1) USB-Soundkarte        ← Einfachste Option / Pi 3 kompatibel"
echo "    2) MAX98357A I2S DAC     ← Wundio HAT / besser, kein USB-Bus-Konflikt"
echo "    3) HifiBerry DAC HAT     ← Tier 3 / Full-Stack (Pi 4/5, belegt 40-Pin)"
echo ""
echo -e "  ${YELLOW}Kann jederzeit in der App unter Einstellungen > Audio geändert werden.${NC}"
echo ""

SETUP_AUDIO_TYPE="usb"

while true; do
    read -r -p "  Deine Wahl [1-3]: " AUDIO_CHOICE
    case "$AUDIO_CHOICE" in
        1)
            SETUP_AUDIO_TYPE="usb"
            ok "USB-Soundkarte"
            break ;;
        2)
            SETUP_AUDIO_TYPE="i2s_max98357"
            ok "MAX98357A I2S DAC (BCLK=BCM18, LRCLK=BCM19, DATA=BCM21)"
            break ;;
        3)
            SETUP_AUDIO_TYPE="hifiberry"
            ok "HifiBerry DAC HAT"
            break ;;
        *)
            echo -e "  ${RED}Ungültige Eingabe. Bitte 1-3 eingeben.${NC}" ;;
    esac
done

# -- 2/10 System packages
section "2/10 Installing system packages"
info "Updating package lists..."
run_spin "apt update" apt-get update

# -- Build install manifest
MANIFEST_DIR="/var/lib/wundio"
mkdir -p "$MANIFEST_DIR"
MANIFEST_FILE="$MANIFEST_DIR/installed-packages.txt"
MANIFEST_META="$MANIFEST_DIR/install-manifest.txt"

APT_PACKAGES=(
    git
    python3 python3-pip python3-venv python3-dev
    build-essential libssl-dev libffi-dev
    i2c-tools libi2c-dev python3-smbus
    hostapd dnsmasq
    libjpeg-dev zlib1g-dev libfreetype6-dev
    curl wget
    alsa-utils
    python3-pillow
    python3-rpi.gpio
    python3-spidev
    nodejs npm
)

info "Checking pre-existing packages..."
> "$MANIFEST_FILE"
for pkg in "${APT_PACKAGES[@]}"; do
    if dpkg -l "$pkg" &>/dev/null 2>&1; then
        echo "pre-existing:$pkg" >> "$MANIFEST_FILE"
    else
        echo "installed-by-wundio:$pkg" >> "$MANIFEST_FILE"
    fi
done

cat > "$MANIFEST_META" << METAEOF
install_date=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
install_user=${SUDO_USER:-root}
pi_model=${HW_MODEL}
pi_generation=${PI_GEN}
git_url=${GIT_URL}
git_branch=${GIT_BRANCH}
display_type=${SETUP_DISPLAY_TYPE}
display_model=${SETUP_DISPLAY_MODEL}
METAEOF

ok "Install manifest created at $MANIFEST_FILE"

info "Installing dependencies (git, python3, i2c-tools, hostapd...)"
run_spin "apt packages" apt-get install -y \
    git \
    python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    i2c-tools libi2c-dev python3-smbus \
    hostapd dnsmasq \
    libjpeg-dev zlib1g-dev libfreetype6-dev \
    curl wget \
    alsa-utils \
    python3-pillow \
    python3-rpi.gpio \
    python3-spidev

# -- 3/10 Enable SPI + I2C
section "3/10 Enabling SPI and I2C"
if command -v raspi-config &>/dev/null; then
    raspi-config nonint do_spi 0
    raspi-config nonint do_i2c 0
    ok "SPI + I2C enabled"
else
    CONFIG_FILE="/boot/firmware/config.txt"
    [[ ! -f "$CONFIG_FILE" ]] && CONFIG_FILE="/boot/config.txt"
    grep -q "^dtparam=spi=on"     "$CONFIG_FILE" || echo "dtparam=spi=on"     >> "$CONFIG_FILE"
    grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE" || echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
    warn "raspi-config not found - appended SPI/I2C to $CONFIG_FILE"
fi

# -- 4/10 Create wundio user & directories
section "4/10 Creating user and directories"
if ! id "$WUNDIO_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false \
            --groups gpio,spi,i2c,audio,video "$WUNDIO_USER" 2>/dev/null || \
    useradd --system --no-create-home --shell /bin/false "$WUNDIO_USER"
    ok "User '$WUNDIO_USER' created"
else
    ok "User '$WUNDIO_USER' already exists"
fi
for grp in gpio spi i2c audio video; do
    getent group "$grp" &>/dev/null && usermod -aG "$grp" "$WUNDIO_USER" || true
done
mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$CONF_DIR"
chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$DATA_DIR"
chown -R root:"$WUNDIO_USER" "$CONF_DIR"
chmod 750 "$CONF_DIR"
ok "Directories ready"

# -- 5/10 Clone / update repo
section "5/10 Fetching Wundio source"
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repo exists - pulling latest $GIT_BRANCH"
    run_spin "git pull" git -C "$INSTALL_DIR" pull origin "$GIT_BRANCH"
elif [[ -f "$(dirname "$0")/../core/main.py" ]]; then
    LOCAL_SRC="$(realpath "$(dirname "$0")/..")"
    info "Local source at $LOCAL_SRC"
    cp -r "$LOCAL_SRC/." "$INSTALL_DIR/"
    ok "Local source copied"
else
    run_spin "git clone" git clone --depth 1 --branch "$GIT_BRANCH" "$GIT_URL" "$INSTALL_DIR"
fi
chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$INSTALL_DIR"
ok "Source ready at $INSTALL_DIR"

# -- 6/10 Python venv
section "6/10 Setting up Python environment"
echo -e "  ${YELLOW}Pi 3: ca. 5-10 Minuten / Pi 4/5: ca. 2-4 Minuten${NC}"
echo -e "  ${YELLOW}   Bitte warten - Python-Pakete werden kompiliert...${NC}"
echo ""

info "Creating virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"

info "Upgrading pip..."
run_spin "pip upgrade" "$VENV_DIR/bin/pip" install --upgrade pip --quiet

info "Installing Wundio Python packages..."
run_spin "pip core deps" "$VENV_DIR/bin/pip" install \
    --prefer-binary \
    --quiet \
    -r "$INSTALL_DIR/core/requirements.txt"

info "Installing hardware packages..."
run_spin "pip hardware" "$VENV_DIR/bin/pip" install \
    --prefer-binary \
    --quiet \
    mfrc522

# Display library – only what's needed for the chosen display type
if [[ "$SETUP_DISPLAY_TYPE" == "oled" ]]; then
    run_spin "pip luma.oled" "$VENV_DIR/bin/pip" install \
        --prefer-binary --quiet "luma.oled"
elif [[ "$SETUP_DISPLAY_TYPE" == "tft" ]]; then
    run_spin "pip luma.lcd" "$VENV_DIR/bin/pip" install \
        --prefer-binary --quiet "luma.lcd"
else
    info "No display selected - skipping luma install"
fi

# PN532 – Adafruit library + blinka (only if PN532 selected)
if [[ "$SETUP_RFID_TYPE" == "pn532" ]]; then
    run_spin "pip pn532" "$VENV_DIR/bin/pip" install \
        --prefer-binary --quiet \
        adafruit-blinka adafruit-circuitpython-pn532
fi

ok "Python environment ready" 

# -- 6b/10 librespot via Raspotify
section "6b/10 Installing Spotify (librespot / Raspotify)"

LS_DONE=false

# Try Raspotify package first (fastest, maintained Debian package)
if curl -fsSL https://dtcooper.github.io/raspotify/install.sh | bash >> "$LOG_FILE" 2>&1; then
    LS_DONE=true
    ok "Raspotify installed"
fi

# Fallback: pre-built librespot binary from GitHub releases
if [[ "$LS_DONE" == "false" ]]; then
    ARCH=$(uname -m)
    case "$ARCH" in
        armv7l)  LS_ASSET="librespot-linux-armv7"  ;;
        aarch64) LS_ASSET="librespot-linux-aarch64" ;;
        x86_64)  LS_ASSET="librespot-linux-x86_64"  ;;
        *)       LS_ASSET="" ;;
    esac
    if [[ -n "$LS_ASSET" ]]; then
        LS_URL="https://github.com/librespot-org/librespot/releases/latest/download/${LS_ASSET}"
        if curl -fsSL "$LS_URL" -o "${INSTALL_DIR}/bin/librespot" >> "$LOG_FILE" 2>&1; then
            chmod +x "${INSTALL_DIR}/bin/librespot"
            LS_DONE=true
            ok "librespot binary installed"
        fi
    fi
fi

# Last resort: build from source (slow on Pi 3, shows live output)
if [[ "$LS_DONE" == "false" ]]; then
    warn "No package available - building librespot from Rust source."
    warn "On Pi 3 this takes 30-60 minutes. Output will be shown live."
    echo ""
    apt-get install -y pkg-config libssl-dev libasound2-dev >> "$LOG_FILE" 2>&1
    if ! command -v cargo &>/dev/null; then
        info "Installing Rust toolchain..."
        curl -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path
    fi
    # shellcheck disable=SC1090
    source "$HOME/.cargo/env" 2>/dev/null || export PATH="$HOME/.cargo/bin:$PATH"
    info "Building librespot - live output below:"
    echo "------------------------------------------"
    cargo install librespot --root "${INSTALL_DIR}" 2>&1 | tee -a "$LOG_FILE"
    echo "------------------------------------------"
    if [[ -f "${INSTALL_DIR}/bin/librespot" ]]; then
        LS_DONE=true
        ok "librespot built from source"
    else
        error "librespot build failed - see $LOG_FILE"
    fi
fi

chmod +x "${INSTALL_DIR}/scripts/librespot-event.sh" 2>/dev/null || true
ok "Spotify (librespot) ready"

# -- 7/10 Build Web Interface
section "7/10 Building Web Interface"
echo -e "  ${YELLOW}Pi 3: ca. 5-15 Minuten / Pi 4/5: ca. 2-5 Minuten${NC}"
echo -e "  ${YELLOW}   Node.js kompiliert die React-App - bitte nicht unterbrechen.${NC}"
echo ""

WEB_DIR="${INSTALL_DIR}/web"
WEB_DIST="${INSTALL_DIR}/core/static/web"

if [[ -d "$WEB_DIR" ]] && [[ -f "$WEB_DIR/package.json" ]]; then
    if ! command -v node &>/dev/null; then
        run_spin "install nodejs" apt-get install -y nodejs npm
    fi
    NODE_VER=$(node --version 2>/dev/null | grep -oP '\d+' | head -1 || echo "0")
    if [[ "$NODE_VER" -lt 18 ]]; then
        info "Node.js v${NODE_VER} too old - installing v20..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - >> "$LOG_FILE" 2>&1
        run_spin "install nodejs 20" apt-get install -y nodejs
    fi
    mkdir -p "$WEB_DIST"
    chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$WEB_DIST"
    chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$WEB_DIR"
    run_spin "npm install" bash -c "cd \"${WEB_DIR}\" && npm install 2>&1"
    run_spin "npm build (1-3 min)" bash -c "cd \"${WEB_DIR}\" && npm run build 2>&1"
    if [[ -f "${WEB_DIST}/index.html" ]]; then
        ok "Web interface ready at ${WEB_DIST}"
    else
        warn "Web build incomplete - retry: cd /opt/wundio/web && npm run build"
    fi
else
    warn "web/ not found - skipping Web UI build (run: cd /opt/wundio/web && npm install && npm run build)"
fi

# -- 8/10 Write configuration
section "8/10 Writing configuration"
cat > "$CONF_DIR/wundio.env" << ENVEOF
# Wundio - Runtime Configuration
# Generated by install.sh on $(date)
# Edit this file or use the web interface at http://wundio.local:8000/settings

APP_VERSION=0.1.0
DEBUG=false
DB_PATH=${DATA_DIR}/wundio.db

# Hardware feature flags (auto-detected - override if needed)
FEAT_SPOTIFY=${FEAT_SPOTIFY}
FEAT_RFID=${FEAT_RFID}
FEAT_DISPLAY_OLED=${FEAT_DISPLAY_OLED}
FEAT_AI_LOCAL=${FEAT_AI_LOCAL}
FEAT_AI_CLOUD=${FEAT_AI_CLOUD}
FEAT_GAMES_ADVANCED=${FEAT_GAMES_ADVANCED}

# WiFi Hotspot (shown on display during setup)
HOTSPOT_SSID=Wundio-Setup
HOTSPOT_PASSWORD=wundio123
HOTSPOT_IP=192.168.50.1

# Spotify / librespot
SPOTIFY_DEVICE_NAME=Wundio
SPOTIFY_BITRATE=160

# RFID reader type (rc522 or pn532 – set by installer)
RFID_TYPE=${SETUP_RFID_TYPE}

# Audio type (usb, i2s_max98357, hifiberry – set by installer)
AUDIO_TYPE=${SETUP_AUDIO_TYPE}

# Hardware pins (BCM numbering)
RFID_RST_PIN=25
BUTTON_PLAY_PAUSE_PIN=17
BUTTON_NEXT_PIN=27
BUTTON_PREV_PIN=22
BUTTON_VOL_UP_PIN=23
BUTTON_VOL_DOWN_PIN=24

# Display – set by installer (change in web interface: Settings > Display)
DISPLAY_TYPE=${SETUP_DISPLAY_TYPE}
DISPLAY_MODEL=${SETUP_DISPLAY_MODEL}
DISPLAY_WIDTH=${SETUP_DISPLAY_WIDTH}
DISPLAY_HEIGHT=${SETUP_DISPLAY_HEIGHT}
DISPLAY_I2C_ADDRESS=0x3C
DISPLAY_I2C_BUS=1
# TFT only (ignored when DISPLAY_TYPE=oled or none):
DISPLAY_SPI_DEV=1
DISPLAY_DC_PIN=16
DISPLAY_RST_PIN=20

# AI / LLM
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
WHISPER_MODEL=tiny
TTS_VOICE=de_DE-thorsten-medium
ENVEOF

chmod 660 "$CONF_DIR/wundio.env"
chown root:"$WUNDIO_USER" "$CONF_DIR/wundio.env"
ok "Config written to $CONF_DIR/wundio.env"

# -- 9/10 systemd services
section "9/10 Installing systemd services"
SYSTEMD_DIR="/etc/systemd/system"
for svc in wundio-core wundio-rfid; do
    cp "$INSTALL_DIR/systemd/${svc}.service" "${SYSTEMD_DIR}/"
done
systemctl daemon-reload
systemctl enable wundio-rfid wundio-core
ok "Services registered and enabled"

# -- 10/10 Start services
section "10/10 Starting Wundio"
systemctl start wundio-rfid wundio-core
sleep 2
if systemctl is-active wundio-core &>/dev/null; then
    ok "wundio-core is running"
else
    warn "wundio-core did not start - check: journalctl -u wundio-core -n 50"
fi

# -- Done
echo ""
echo -e "${BOLD}${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  Wundio installation complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  ${BOLD}Web interface:${NC}  http://wundio.local:8000"
echo -e "  ${BOLD}Config:${NC}         /etc/wundio/wundio.env"
echo -e "  ${BOLD}Logs:${NC}           journalctl -u wundio-core -f"
echo -e "  ${BOLD}Display:${NC}        ${SETUP_DISPLAY_TYPE} / ${SETUP_DISPLAY_MODEL}"
echo ""
if [[ "$SETUP_DISPLAY_TYPE" == "tft" ]]; then
    echo -e "  ${YELLOW}TFT-Display: Pinout prüfen unter wundio.dev/docs/hardware${NC}"
    echo ""
fi
echo -e "  ${BLUE}Docs & Community:  wundio.dev${NC}"
echo ""