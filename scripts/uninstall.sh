#!/usr/bin/env bash
# Wundio – Uninstall Script
# Entfernt alle Wundio-Dienste, Dateien und Konfigurationen vollständig.
# Der Raspberry Pi wird in den Zustand vor der Installation zurückversetzt.
#
# Ausführen: sudo bash /opt/wundio/scripts/uninstall.sh
# Oder:      curl -fsSL https://wundio.dev/uninstall.sh | sudo bash

set -euo pipefail

LOG_FILE="/var/log/wundio-uninstall.log"
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
section() { echo -e "\n${BOLD}${CYAN}━━━  $*  ━━━${NC}" | tee -a "$LOG_FILE"; }

# ── Root check ────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && echo "Run as root: sudo bash uninstall.sh" && exit 1

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== Wundio uninstall $(date) ===" >> "$LOG_FILE"

# ── Banner ────────────────────────────────────────────────────────────────────
echo -e "${BOLD}"
cat << 'EOF'
 __        __              _ _
 \ \      / /   _ _ __   __| (_) ___
  \ \ /\ / / | | | '_ \ / _` | |/ _ \
   \ V  V /| |_| | | | | (_| | | (_) |
    \_/\_/  \__,_|_| |_|\__,_|_|\___/

  Uninstall – Wundio vollständig entfernen
EOF
echo -e "${NC}"

echo -e "${YELLOW}${BOLD}  Achtung: Diese Aktion kann nicht rückgängig gemacht werden.${NC}"
echo -e "  Alle Wundio-Daten, Konfigurationen und Dienste werden entfernt."
echo ""
read -rp "  Wirklich deinstallieren? [ja/N] " ans
[[ "${ans,,}" != "ja" ]] && echo "Abgebrochen." && exit 0

echo ""

# ── 1. Stop and disable all services ─────────────────────────────────────────
section "1/7  Stopping services"

SERVICES=(
    wundio-core
    wundio-rfid
    wundio-hotspot
)

for svc in "${SERVICES[@]}"; do
    if systemctl list-unit-files --quiet "${svc}.service" &>/dev/null; then
        info "Stopping ${svc}..."
        systemctl stop    "${svc}" 2>/dev/null || true
        systemctl disable "${svc}" 2>/dev/null || true
        ok "${svc} stopped and disabled"
    else
        info "${svc} not installed – skipping"
    fi
done

# Kill any remaining processes on port 8000
if command -v fuser &>/dev/null; then
    fuser -k 8000/tcp 2>/dev/null || true
fi
# Kill stray uvicorn / hostapd
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "hostapd.*wundio"   2>/dev/null || true
ok "All processes stopped"

# ── 2. Remove systemd service files ──────────────────────────────────────────
section "2/7  Removing systemd units"

SYSTEMD_DIR="/etc/systemd/system"
for svc in "${SERVICES[@]}"; do
    FILE="${SYSTEMD_DIR}/${svc}.service"
    if [[ -f "$FILE" ]]; then
        rm -f "$FILE"
        ok "Removed ${FILE}"
    fi
done
systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true
ok "systemd cleaned up"

# ── 3. Remove hostapd + dnsmasq config ───────────────────────────────────────
section "3/7  Removing network configuration"

# hostapd config
rm -f /etc/hostapd/wundio-hostapd.conf
ok "Removed hostapd config"

# dnsmasq config
rm -f /etc/dnsmasq.d/wundio-hotspot.conf
ok "Removed dnsmasq hotspot config"

# Restart dnsmasq without wundio config (system may still use it)
systemctl restart dnsmasq 2>/dev/null || true

# Restore wpa_supplicant if it was stopped
if ! systemctl is-active --quiet wpa_supplicant 2>/dev/null; then
    info "Restarting wpa_supplicant..."
    systemctl start wpa_supplicant 2>/dev/null || true
fi

# Restore NetworkManager wlan0 management if it was unmanaged
if command -v nmcli &>/dev/null; then
    nmcli dev set wlan0 managed yes 2>/dev/null || true
fi

ok "Network configuration restored"

# ── 4. Remove Raspotify / librespot ──────────────────────────────────────────
section "4/7  Removing Spotify (librespot / Raspotify)"

if systemctl list-unit-files --quiet raspotify.service &>/dev/null; then
    systemctl stop    raspotify 2>/dev/null || true
    systemctl disable raspotify 2>/dev/null || true
    ok "Raspotify service disabled"
fi

if command -v apt-get &>/dev/null; then
    apt-get remove -y raspotify librespot 2>/dev/null || true
    # Remove Raspotify apt repo
    rm -f /etc/apt/sources.list.d/raspotify.list
    rm -f /etc/apt/trusted.gpg.d/raspotify.gpg
    rm -f /usr/share/keyrings/raspotify-archive-keyring.gpg
    apt-get update -qq 2>/dev/null || true
fi

ok "Spotify packages removed"

# ── 5. Remove all Wundio files ────────────────────────────────────────────────
section "5/7  Removing Wundio files"

DIRS_TO_REMOVE=(
    "/opt/wundio"          # main install: core, venv, web, scripts
    "/var/lib/wundio"      # database and runtime data
    "/etc/wundio"          # configuration
)

for dir in "${DIRS_TO_REMOVE[@]}"; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        ok "Removed $dir"
    else
        info "$dir not found – skipping"
    fi
done

# Log files
rm -f /var/log/wundio-install.log
rm -f /var/log/wundio-update.log
rm -f /var/log/wundio-uninstall.log   # will be recreated for this session
ok "Log files removed"

# Runtime temp files
rm -f /tmp/wundio-player.json
ok "Temp files removed"

# ── 6. Remove wundio user ─────────────────────────────────────────────────────
section "6/7  Removing system user"

if id wundio &>/dev/null; then
    userdel wundio 2>/dev/null || true
    ok "User 'wundio' removed"
else
    info "User 'wundio' not found – skipping"
fi

# ── 7. Optional: remove apt packages installed by Wundio ─────────────────────
section "7/7  Optional cleanup"

echo ""
echo -e "  The following packages were installed by Wundio."
echo -e "  They may also be used by other programs on your system."
echo ""
echo -e "    hostapd  dnsmasq  alsa-utils  i2c-tools"
echo -e "    python3-rpi.gpio  python3-spidev  python3-pillow"
echo ""
read -rp "  Remove these packages too? [j/N] " remove_pkgs
if [[ "${remove_pkgs,,}" == "j" ]]; then
    apt-get remove -y \
        hostapd dnsmasq alsa-utils i2c-tools \
        python3-rpi.gpio python3-spidev python3-pillow \
        2>/dev/null || true
    apt-get autoremove -y 2>/dev/null || true
    ok "Additional packages removed"
else
    info "Packages kept"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓  Wundio vollständig entfernt${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Entfernt:"
echo -e "    ✓ Alle systemd-Dienste (wundio-core, wundio-rfid, wundio-hotspot)"
echo -e "    ✓ Port 8000 freigegeben"
echo -e "    ✓ Hotspot-Konfiguration (hostapd, dnsmasq)"
echo -e "    ✓ Alle Dateien unter /opt/wundio, /var/lib/wundio, /etc/wundio"
echo -e "    ✓ System-User 'wundio'"
echo -e "    ✓ librespot / Raspotify"
echo ""
echo -e "  Der Raspberry Pi kann jetzt wieder anderweitig genutzt werden."
echo -e "  Ein Neustart wird empfohlen: ${YELLOW}sudo reboot${NC}"
echo ""