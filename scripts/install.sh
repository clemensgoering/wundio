#!/usr/bin/env bash
# Wundio – Installation Script
# Usage: curl -fsSL https://wundio.dev/install.sh | sudo bash
# Or:   sudo bash scripts/install.sh

set -euo pipefail

# ── Config ────────────────────────────────────────────────────────────────────
GIT_URL="${WUNDIO_GIT_URL:-https://github.com/clemensgoering/wundio.git}"
GIT_BRANCH="${WUNDIO_BRANCH:-main}"
INSTALL_DIR="/opt/wundio"
DATA_DIR="/var/lib/wundio"
CONF_DIR="/etc/wundio"
VENV_DIR="${INSTALL_DIR}/venv"
WUNDIO_USER="wundio"
LOG_FILE="/var/log/wundio-install.log"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERR ]${NC}  $*" | tee -a "$LOG_FILE"; exit 1; }
section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BOLD}${CYAN}━━━  $*  ━━━${NC}" | tee -a "$LOG_FILE"
}

# ── Spinner ───────────────────────────────────────────────────────────────────
# Usage: long_command | spin "Label"
# Or:    spin "Label" & SPIN_PID=$!; long_command; kill $SPIN_PID
_spin_frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
spin_bg() {
    # Runs in background, prints spinner until killed
    local label="$1"
    local i=0
    while true; do
        printf "\r  ${CYAN}${_spin_frames[$i]}${NC}  %s..." "$label" >&2
        i=$(( (i+1) % ${#_spin_frames[@]} ))
        sleep 0.12
    done
}

run_spin() {
    # run_spin "Label" command args...
    local label="$1"; shift
    spin_bg "$label" &
    local SPIN_PID=$!
    # Run command, capture exit code, log all output
    set +e
    "$@" >> "$LOG_FILE" 2>&1
    local EXIT_CODE=$?
    set -e
    kill $SPIN_PID 2>/dev/null; wait $SPIN_PID 2>/dev/null || true
    printf "\r  %-60s\n" "" >&2   # clear spinner line
    if [[ $EXIT_CODE -eq 0 ]]; then
        ok "$label"
    else
        error "$label failed (exit $EXIT_CODE) – see $LOG_FILE"
    fi
    return $EXIT_CODE
}

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

  Interactive Box for Kids – wundio.dev
EOF
echo -e "${NC}"

# ── 1. Hardware Detection ─────────────────────────────────────────────────────
section "1/9  Detecting hardware"

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

PI_GEN=0
if [[ "$HW_MODEL" =~ "Raspberry Pi 5" ]];      then PI_GEN=5
elif [[ "$HW_MODEL" =~ "Raspberry Pi 4" ]];    then PI_GEN=4
elif [[ "$HW_MODEL" =~ "Raspberry Pi 3" ]];    then PI_GEN=3
elif [[ "$HW_MODEL" =~ "Raspberry Pi Zero 2" ]];then PI_GEN=3
elif [[ "$HW_MODEL" =~ "Raspberry Pi 2" ]];    then PI_GEN=2
else PI_GEN=3; fi

info "Pi generation: ${PI_GEN}"

FEAT_SPOTIFY=true; FEAT_RFID=true; FEAT_DISPLAY_OLED=true; FEAT_BUTTONS=true
FEAT_AI_LOCAL=false; FEAT_AI_CLOUD=false; FEAT_GAMES_ADVANCED=false
[[ $PI_GEN -ge 4 ]] && FEAT_AI_CLOUD=true && FEAT_GAMES_ADVANCED=true
[[ $PI_GEN -ge 5 && $RAM_MB -ge 7000 ]] && FEAT_AI_LOCAL=true

# Time estimate
case $PI_GEN in
    3) EST="15–25 min" ;;
    4) EST="8–15 min"  ;;
    5) EST="5–10 min"  ;;
    *) EST="10–20 min" ;;
esac
echo ""
echo -e "  ${YELLOW}Estimated installation time on Pi ${PI_GEN}: ${EST}${NC}"
echo -e "  ${YELLOW}Please do not interrupt the installation.${NC}"
echo ""
ok "Hardware detected – Pi ${PI_GEN}, ${RAM_MB} MB RAM"

# ── 2. System packages ────────────────────────────────────────────────────────
section "2/9  Installing system packages"
info "Updating package lists..."
run_spin "apt update" apt-get update

info "Installing dependencies (git, python3, i2c-tools, hostapd…)"
# Use apt for as many packages as possible to avoid pip compilation later
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

# ── 3. Enable SPI + I2C ───────────────────────────────────────────────────────
section "3/9  Enabling SPI and I2C"
if command -v raspi-config &>/dev/null; then
    raspi-config nonint do_spi 0
    raspi-config nonint do_i2c 0
    ok "SPI + I2C enabled"
else
    CONFIG_FILE="/boot/firmware/config.txt"
    [[ ! -f "$CONFIG_FILE" ]] && CONFIG_FILE="/boot/config.txt"
    grep -q "^dtparam=spi=on"     "$CONFIG_FILE" || echo "dtparam=spi=on"     >> "$CONFIG_FILE"
    grep -q "^dtparam=i2c_arm=on" "$CONFIG_FILE" || echo "dtparam=i2c_arm=on" >> "$CONFIG_FILE"
    warn "raspi-config not found – appended SPI/I2C to $CONFIG_FILE"
fi

# ── 4. Create wundio user & directories ──────────────────────────────────────
section "4/9  Creating user and directories"
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

# ── 5. Clone / update repo ────────────────────────────────────────────────────
section "5/9  Fetching Wundio source"
if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Repo exists – pulling latest $GIT_BRANCH"
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

# ── 6. Python venv ────────────────────────────────────────────────────────────
section "6/9  Setting up Python environment"

info "Creating virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"
# --system-site-packages reuses apt-installed Pillow, RPi.GPIO, spidev
# This avoids slow compilation steps entirely

info "Upgrading pip..."
run_spin "pip upgrade" "$VENV_DIR/bin/pip" install --upgrade pip --quiet

info "Installing Wundio Python packages..."
run_spin "pip core deps" "$VENV_DIR/bin/pip" install \
    --prefer-binary \
    --quiet \
    -r "$INSTALL_DIR/core/requirements.txt"

info "Installing hardware packages..."
# mfrc522 is small and has a wheel; luma.oled links against system Pillow
run_spin "pip hardware" "$VENV_DIR/bin/pip" install \
    --prefer-binary \
    --quiet \
    mfrc522 \
    "luma.oled"
ok "Python environment ready"

# ── 6b. librespot (Spotify) ───────────────────────────────────────────────────
if [[ "$FEAT_SPOTIFY" == "true" ]]; then
    section "6b/9  Installing librespot (Spotify Connect)"
    LIBRESPOT_BIN="${INSTALL_DIR}/bin/librespot"
    mkdir -p "${INSTALL_DIR}/bin"
    ARCH=$(uname -m)
    case "$ARCH" in
        aarch64|arm64) LS_ARCH="aarch64-unknown-linux-gnu"    ;;
        armv7l)        LS_ARCH="armv7-unknown-linux-gnueabihf" ;;
        armv6l)        LS_ARCH="arm-unknown-linux-gnueabihf"   ;;
        x86_64)        LS_ARCH="x86_64-unknown-linux-gnu"      ;;
        *)             LS_ARCH="" ;;
    esac
    LS_DONE=false

    # 1. apt (Bookworm has it)
    if apt-cache show librespot &>/dev/null 2>&1; then
        run_spin "librespot via apt" apt-get install -y librespot
        ln -sf "$(which librespot)" "$LIBRESPOT_BIN" 2>/dev/null || true
        LS_DONE=true

    # 2. prebuilt binary from GitHub releases
    elif [[ -n "$LS_ARCH" ]]; then
        LS_VER="0.5.0"
        LS_URL="https://github.com/librespot-org/librespot/releases/download/v${LS_VER}/librespot-${LS_ARCH}.tar.gz"
        info "Downloading librespot ${LS_VER} for ${LS_ARCH}..."
        if curl -fsSL --progress-bar "$LS_URL" -o /tmp/librespot.tar.gz; then
            tar -xzf /tmp/librespot.tar.gz -C "${INSTALL_DIR}/bin/" librespot 2>/dev/null || \
            tar -xzf /tmp/librespot.tar.gz -C "${INSTALL_DIR}/bin/"
            chmod +x "${INSTALL_DIR}/bin/librespot" 2>/dev/null || true
            rm -f /tmp/librespot.tar.gz
            LS_DONE=true
            ok "librespot binary ready"
        else
            warn "Could not download librespot binary"
        fi
    fi

    # 3. build from source (last resort – slow, warn user)
    if [[ "$LS_DONE" == "false" ]]; then
        warn "No prebuilt binary available – building from source."
        warn "This can take 20–40 minutes on Pi 3. Please be patient."
        if ! command -v cargo &>/dev/null; then
            info "Installing Rust toolchain..."
            curl -fsSL https://sh.rustup.rs | sh -s -- -y --no-modify-path
            export PATH="$HOME/.cargo/bin:$PATH"
        fi
        run_spin "apt build deps" apt-get install -y pkg-config libssl-dev libasound2-dev
        run_spin "cargo build librespot" cargo install librespot --root "${INSTALL_DIR}"
    fi

    chmod +x "${INSTALL_DIR}/scripts/librespot-event.sh" 2>/dev/null || true
    ok "Spotify (librespot) ready"
fi

# ── 7. Write config env ───────────────────────────────────────────────────────
section "7/9  Writing configuration"
cat > "$CONF_DIR/wundio.env" << ENVEOF
# Wundio – Runtime Configuration
# Generated by install.sh on $(date)
# Edit this file to customise your setup, then: sudo systemctl restart wundio-core

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

# Hardware pins (BCM numbering)
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
section "8/9  Installing systemd services"
SYSTEMD_DIR="/etc/systemd/system"
for svc in wundio-core wundio-rfid; do
    cp "$INSTALL_DIR/systemd/${svc}.service" "${SYSTEMD_DIR}/"
done
systemctl daemon-reload
systemctl enable wundio-rfid wundio-core
ok "Services registered and enabled"

# ── 9. WiFi Hotspot setup ─────────────────────────────────────────────────────
section "9/9  Setting up WiFi hotspot"
run_spin "hotspot setup" bash "$INSTALL_DIR/scripts/setup-hotspot.sh"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓  Wundio installation complete!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Next steps:"
echo -e "  1. Connect to WiFi:  ${YELLOW}Wundio-Setup${NC}  (Password: ${YELLOW}wundio123${NC})"
echo -e "  2. Open in browser:  ${YELLOW}http://192.168.50.1:8000${NC}"
echo -e "  3. Enter your home WiFi and complete setup"
echo ""
echo -e "  Full log: ${LOG_FILE}"
echo ""

if command -v raspi-config &>/dev/null; then
    read -rp "  Reboot now to activate SPI/I2C? [Y/n] " ans
    [[ "${ans:-Y}" =~ ^[Yy]$ ]] && reboot
else
    warn "Please reboot manually, then: sudo systemctl start wundio-core"
fi