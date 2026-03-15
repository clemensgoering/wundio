#!/usr/bin/env bash
# Wundio – Installation Script
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_ORG/wundio/main/scripts/install.sh | sudo bash
# Or:   sudo bash scripts/install.sh
#
# This script:
#   1. Detects Raspberry Pi model & sets feature flags
#   2. Installs system dependencies
#   3. Enables SPI + I2C interfaces
#   4. Creates wundio user & directories
#   5. Clones the repo (or uses local path)
#   6. Sets up Python venv + installs packages
#   7. Writes /etc/wundio/wundio.env
#   8. Registers & starts systemd services
#   9. Activates WiFi hotspot for first-run setup

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
GIT_URL="${WUNDIO_GIT_URL:-https://github.com/YOUR_ORG/wundio.git}"
GIT_BRANCH="${WUNDIO_BRANCH:-main}"
INSTALL_DIR="/opt/wundio"
DATA_DIR="/var/lib/wundio"
CONF_DIR="/etc/wundio"
VENV_DIR="${INSTALL_DIR}/venv"
WUNDIO_USER="wundio"
LOG_FILE="/var/log/wundio-install.log"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[OK]${NC}    $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; exit 1; }
section() { echo -e "\n${BOLD}▶ $*${NC}" | tee -a "$LOG_FILE"; }

# ── Root check ────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Please run as root: sudo bash install.sh"

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== Wundio install $(date) ===" >> "$LOG_FILE"

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
cat << 'EOF'
 __        __              _ _
 \ \      / /   _ _ __   __| (_) ___
  \ \ /\ / / | | | '_ \ / _` | |/ _ \
   \ V  V /| |_| | | | | (_| | | (_) |
    \_/\_/  \__,_|_| |_|\__,_|_|\___/

  Interactive Box for Kids
  github.com/YOUR_ORG/wundio
EOF
echo -e "${NC}"

# ── 1. Hardware Detection ─────────────────────────────────────────────────────
section "Detecting hardware"

MODEL_FILE="/proc/device-tree/model"
if [[ -f "$MODEL_FILE" ]]; then
    HW_MODEL=$(tr -d '\0' < "$MODEL_FILE")
    info "Model: $HW_MODEL"
else
    HW_MODEL="unknown"
    warn "Could not detect Pi model – assuming Pi 3 (minimal features)"
fi

RAM_MB=$(awk '/MemTotal/{print int($2/1024)}' /proc/meminfo)
info "RAM: ${RAM_MB} MB"

# Parse Pi generation
PI_GEN=0
if [[ "$HW_MODEL" =~ "Raspberry Pi 5" ]]; then PI_GEN=5
elif [[ "$HW_MODEL" =~ "Raspberry Pi 4" ]]; then PI_GEN=4
elif [[ "$HW_MODEL" =~ "Raspberry Pi 3" ]]; then PI_GEN=3
elif [[ "$HW_MODEL" =~ "Raspberry Pi Zero 2" ]]; then PI_GEN=3  # similar perf
elif [[ "$HW_MODEL" =~ "Raspberry Pi 2" ]]; then PI_GEN=2
else PI_GEN=3; fi

info "Pi generation: ${PI_GEN}"

# Feature flags
FEAT_SPOTIFY=true
FEAT_RFID=true
FEAT_DISPLAY_OLED=true
FEAT_BUTTONS=true
FEAT_AI_LOCAL=false
FEAT_AI_CLOUD=false
FEAT_GAMES_ADVANCED=false

[[ $PI_GEN -ge 4 ]] && FEAT_AI_CLOUD=true && FEAT_GAMES_ADVANCED=true
[[ $PI_GEN -ge 5 && $RAM_MB -ge 7000 ]] && FEAT_AI_LOCAL=true

ok "Feature flags set:"
echo "  spotify=$FEAT_SPOTIFY | rfid=$FEAT_RFID | oled=$FEAT_DISPLAY_OLED"
echo "  ai_local=$FEAT_AI_LOCAL | ai_cloud=$FEAT_AI_CLOUD | games_adv=$FEAT_GAMES_ADVANCED"

# ── 2. System packages ────────────────────────────────────────────────────────
section "Installing system packages"
apt-get update -qq
apt-get install -y -qq \
    git python3 python3-pip python3-venv python3-dev \
    build-essential libssl-dev libffi-dev \
    i2c-tools libi2c-dev \
    python3-smbus \
    hostapd dnsmasq \
    libjpeg-dev zlib1g-dev libfreetype6-dev \
    curl wget
ok "System packages installed"

# ── 3. Enable SPI + I2C ───────────────────────────────────────────────────────
section "Enabling SPI and I2C interfaces"
# raspi-config nonint: 0 = enabled, 1 = disabled
if command -v raspi-config &>/dev/null; then
    raspi-config nonint do_spi 0
    raspi-config nonint do_i2c 0
    ok "SPI + I2C enabled via raspi-config"
else
    # Manual fallback – add to /boot/config.txt
    CONFIG_FILE="/boot/firmware/config.txt"
    [[ ! -f "$CONFIG_FILE" ]] && CONFIG_FILE="/boot/config.txt"
    grep -q "^dtparam=spi=on" "$CONFIG_FILE" || echo "dtparam=spi=on" >> "$CONFIG_FILE"
    grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE" || echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
    warn "raspi-config not found – manually appended SPI/I2C to $CONFIG_FILE (reboot needed)"
fi

# ── 4. Create wundio user & directories ──────────────────────────────────────
section "Creating user and directories"
if ! id "$WUNDIO_USER" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false \
            --groups gpio,spi,i2c,audio,video "$WUNDIO_USER" 2>/dev/null || \
    useradd --system --no-create-home --shell /bin/false "$WUNDIO_USER"
    ok "User '$WUNDIO_USER' created"
else
    ok "User '$WUNDIO_USER' already exists"
fi

# Add to hardware groups (best-effort)
for grp in gpio spi i2c audio video; do
    getent group "$grp" &>/dev/null && usermod -aG "$grp" "$WUNDIO_USER" || true
done

mkdir -p "$INSTALL_DIR" "$DATA_DIR" "$CONF_DIR"
chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$DATA_DIR"
chown -R root:"$WUNDIO_USER" "$CONF_DIR"
chmod 750 "$CONF_DIR"

# ── 5. Clone / update repo ────────────────────────────────────────────────────
section "Fetching Wundio source"
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repo exists – pulling latest $GIT_BRANCH"
    git -C "$INSTALL_DIR" fetch origin
    git -C "$INSTALL_DIR" checkout "$GIT_BRANCH"
    git -C "$INSTALL_DIR" pull origin "$GIT_BRANCH"
elif [[ -f "$(dirname "$0")/../core/main.py" ]]; then
    # Running from local checkout
    LOCAL_SRC="$(realpath "$(dirname "$0")/..")"
    info "Local source detected at $LOCAL_SRC"
    cp -r "$LOCAL_SRC/." "$INSTALL_DIR/"
else
    git clone --depth 1 --branch "$GIT_BRANCH" "$GIT_URL" "$INSTALL_DIR"
fi
chown -R "$WUNDIO_USER":"$WUNDIO_USER" "$INSTALL_DIR"
ok "Source ready at $INSTALL_DIR"

# ── 6. Python venv ────────────────────────────────────────────────────────────
section "Setting up Python environment"
python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip -q

# Base requirements
"$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/core/requirements.txt" -q

# Hardware packages (only on actual Pi)
if [[ "$HW_MODEL" != "unknown" ]]; then
    info "Installing hardware packages (SPI, GPIO, RFID, OLED)..."
    "$VENV_DIR/bin/pip" install \
        RPi.GPIO spidev mfrc522 \
        "luma.oled" Pillow -q
    ok "Hardware packages installed"
fi

# AI packages – only if feature_ai_local
if [[ "$FEAT_AI_LOCAL" == "true" ]]; then
    info "Installing Whisper (tiny model) for speech recognition..."
    "$VENV_DIR/bin/pip" install openai-whisper -q
fi

ok "Python environment ready"

# ── 7. Write config env ───────────────────────────────────────────────────────
section "Writing configuration"

cat > "$CONF_DIR/wundio.env" << ENVEOF
# Wundio – Runtime Configuration
# Generated by install.sh on $(date)
# Edit this file to customise your setup.

APP_VERSION=0.1.0
DEBUG=false
DB_PATH=${DATA_DIR}/wundio.db

# Hardware feature flags (auto-detected – override if needed)
FEAT_SPOTIFY=${FEAT_SPOTIFY}
FEAT_RFID=${FEAT_RFID}
FEAT_DISPLAY_OLED=${FEAT_DISPLAY_OLED}
FEAT_AI_LOCAL=${FEAT_AI_LOCAL}
FEAT_AI_CLOUD=${FEAT_AI_CLOUD}
FEAT_GAMES_ADVANCED=${FEAT_GAMES_ADVANCED}

# WiFi Hotspot (shown on OLED during setup)
HOTSPOT_SSID=Wundio-Setup
HOTSPOT_PASSWORD=wundio123
HOTSPOT_IP=192.168.50.1

# Spotify / librespot
SPOTIFY_DEVICE_NAME=Wundio
SPOTIFY_BITRATE=160

# Hardware pins (BCM)
RFID_RST_PIN=25
BUTTON_PLAY_PAUSE_PIN=17
BUTTON_NEXT_PIN=27
BUTTON_PREV_PIN=22
BUTTON_VOL_UP_PIN=23
BUTTON_VOL_DOWN_PIN=24

# OLED I2C
DISPLAY_I2C_ADDRESS=0x3C
DISPLAY_I2C_BUS=1
ENVEOF

chmod 640 "$CONF_DIR/wundio.env"
chown root:"$WUNDIO_USER" "$CONF_DIR/wundio.env"
ok "Config written to $CONF_DIR/wundio.env"

# ── 8. systemd services ───────────────────────────────────────────────────────
section "Installing systemd services"
SYSTEMD_DIR="/etc/systemd/system"
for svc in wundio-core wundio-rfid; do
    cp "$INSTALL_DIR/systemd/${svc}.service" "${SYSTEMD_DIR}/"
done
systemctl daemon-reload
systemctl enable wundio-rfid wundio-core
ok "Services registered"

# ── 9. WiFi Hotspot setup ─────────────────────────────────────────────────────
section "Setting up first-run WiFi hotspot"
bash "$INSTALL_DIR/scripts/setup-hotspot.sh"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}✓ Wundio installation complete!${NC}"
echo ""
echo "  Next steps:"
echo "  1. Connect to WiFi: ${YELLOW}Wundio-Setup${NC}  Password: ${YELLOW}wundio123${NC}"
echo "  2. Open browser:    ${YELLOW}http://192.168.50.1:8000${NC}"
echo "  3. Complete setup & connect to your home WiFi"
echo ""
echo -e "  Log: ${LOG_FILE}"
echo ""

# Offer immediate start or prompt for reboot (SPI/I2C may need reboot)
if command -v raspi-config &>/dev/null; then
    read -rp "  Reboot now to activate SPI/I2C? [Y/n] " ans
    [[ "${ans:-Y}" =~ ^[Yy]$ ]] && reboot
else
    warn "Please reboot manually to activate SPI/I2C, then run: systemctl start wundio-core"
fi
