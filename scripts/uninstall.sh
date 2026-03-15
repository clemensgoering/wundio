#!/usr/bin/env bash
# Wundio - Uninstall Script
# Entfernt Wundio vollständig. Pakete die vor der Installation bereits
# vorhanden waren, werden NICHT entfernt (Install-Manifest wird geprüft).
#
# Ausführen: sudo bash /opt/wundio/scripts/uninstall.sh
# Oder:      curl -fsSL https://wundio.dev/uninstall.sh | sudo bash

set -euo pipefail

LOG_FILE="/tmp/wundio-uninstall.log"
MANIFEST_FILE="/var/lib/wundio/installed-packages.txt"
MANIFEST_META="/var/lib/wundio/install-manifest.txt"

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
skip()    { echo -e "  ${CYAN}[SKIP]${NC}  $* (war vor Wundio vorhanden)" | tee -a "$LOG_FILE"; }
section() { echo -e "\n${BOLD}-- $* --${NC}" | tee -a "$LOG_FILE"; }

# -- Root check
[[ $EUID -ne 0 ]] && echo "Run as root: sudo bash uninstall.sh" && exit 1

echo "=== Wundio uninstall $(date) ===" > "$LOG_FILE"

# -- Banner
echo -e "${BOLD}"
cat << 'EOF'
 __        __              _ _
 \ \      / /   _ _ __   __| (_) ___
  \ \ /\ / / | | | '_ \ / _` | |/ _ \
   \ V  V /| |_| | | | | (_| | | (_) |
    \_/\_/  \__,_|_| |_|\__,_|_|\___/

  Wundio deinstallieren
EOF
echo -e "${NC}"

# -- Show install info if manifest exists
if [[ -f "$MANIFEST_META" ]]; then
    echo -e "  ${CYAN}Installation vom:${NC}"
    grep "install_date" "$MANIFEST_META" | sed 's/install_date=/    /' || true
    grep "pi_model"     "$MANIFEST_META" | sed 's/pi_model=/    Pi: /' || true
    echo ""
fi

echo -e "  ${YELLOW}${BOLD}Achtung: Alle Wundio-Daten und Konfigurationen werden entfernt.${NC}"

# -- Interactive confirmation
# Safe for both direct execution and curl|bash
if [[ -t 0 ]]; then
    # Running interactively - ask user
    read -rp "  Wirklich deinstallieren? [ja/N] " ans
    if [[ "$ans" != "ja" && "$ans" != "Ja" && "$ans" != "JA" ]]; then
        echo "Abgebrochen."
        exit 0
    fi
else
    # Piped (curl|bash) - default safe: abort
    echo ""
    echo -e "  ${RED}Kein interaktiver Modus erkannt (curl|bash).${NC}"
    echo -e "  Bitte direkt ausführen:"
    echo -e "  ${YELLOW}sudo bash /opt/wundio/scripts/uninstall.sh${NC}"
    echo ""
    exit 1
fi

echo ""

# -- Helper: was this package installed by Wundio?
_wundio_installed_pkg() {
    local pkg="$1"
    if [[ ! -f "$MANIFEST_FILE" ]]; then
        # No manifest -> installed before we tracked - be conservative, skip removal
        return 1
    fi
    grep -q "^installed-by-wundio:${pkg}$" "$MANIFEST_FILE" 2>/dev/null
}

# -- 1. Stop and disable all services
section "1/6  Stopping services"

for svc in wundio-core wundio-rfid wundio-hotspot; do
    if systemctl list-unit-files "${svc}.service" &>/dev/null 2>&1; then
        systemctl stop    "$svc" 2>/dev/null || true
        systemctl disable "$svc" 2>/dev/null || true
        ok "$svc stopped and disabled"
    fi
done

# Release port 8000
if command -v fuser &>/dev/null; then
    fuser -k 8000/tcp 2>/dev/null || true
fi
pkill -f "uvicorn.*main:app" 2>/dev/null || true
pkill -f "hostapd.*wundio"   2>/dev/null || true
ok "Port 8000 freigegeben"

# -- 2. Remove systemd service files
section "2/6  Removing systemd units"

for svc in wundio-core wundio-rfid wundio-hotspot; do
    FILE="/etc/systemd/system/${svc}.service"
    if [[ -f "$FILE" ]]; then
        rm -f "$FILE"
        ok "Removed $FILE"
    fi
done
systemctl daemon-reload
systemctl reset-failed 2>/dev/null || true
ok "systemd bereinigt"

# -- 3. Remove network config (only Wundio-specific files)
section "3/6  Restoring network configuration"

# Only remove our specific config files, never touch base hostapd/dnsmasq config
rm -f /etc/hostapd/wundio-hostapd.conf
ok "hostapd config entfernt"

rm -f /etc/dnsmasq.d/wundio-hotspot.conf
ok "dnsmasq hotspot config entfernt"

# Restart dnsmasq if it's still running (may have other configs)
systemctl restart dnsmasq 2>/dev/null || true

# Restore wpa_supplicant if we stopped it
systemctl start wpa_supplicant 2>/dev/null || true

# Re-enable NetworkManager wlan management
if command -v nmcli &>/dev/null; then
    nmcli dev set wlan0 managed yes 2>/dev/null || true
fi

ok "Netzwerk wiederhergestellt"

# -- 4. Remove Raspotify (only if Wundio installed it)
section "4/6  Removing Spotify (librespot)"

if _wundio_installed_pkg "raspotify" || _wundio_installed_pkg "librespot"; then
    systemctl stop    raspotify 2>/dev/null || true
    systemctl disable raspotify 2>/dev/null || true
    apt-get remove -y raspotify librespot 2>/dev/null || true
    # Remove Raspotify apt repo
    rm -f /etc/apt/sources.list.d/raspotify.list
    rm -f /etc/apt/trusted.gpg.d/raspotify.gpg
    rm -f /usr/share/keyrings/raspotify-archive-keyring.gpg
    apt-get update -qq 2>/dev/null || true
    ok "Raspotify/librespot entfernt"
else
    skip "librespot/raspotify (nicht durch Wundio installiert)"
fi

# -- 5. Remove apt packages (only those Wundio installed)
section "5/6  Removing packages (nur Wundio-eigene)"

if [[ ! -f "$MANIFEST_FILE" ]]; then
    warn "Kein Install-Manifest gefunden (/var/lib/wundio/installed-packages.txt)"
    warn "Pakete werden NICHT entfernt um bestehende Setups nicht zu beschädigen."
    warn "Tipp: Pakete manuell prüfen mit: apt list --installed | grep <paketname>"
else
    PKGS_TO_REMOVE=()
    while IFS=: read -r status pkg; do
        if [[ "$status" == "installed-by-wundio" ]]; then
            PKGS_TO_REMOVE+=("$pkg")
        elif [[ "$status" == "pre-existing" ]]; then
            skip "$pkg"
        fi
    done < "$MANIFEST_FILE"

    if [[ ${#PKGS_TO_REMOVE[@]} -gt 0 ]]; then
        info "Entferne Wundio-eigene Pakete: ${PKGS_TO_REMOVE[*]}"
        apt-get remove -y "${PKGS_TO_REMOVE[@]}" 2>/dev/null || true
        apt-get autoremove -y 2>/dev/null || true
        ok "Pakete entfernt: ${#PKGS_TO_REMOVE[@]} Stück"
    else
        info "Keine Wundio-eigenen Pakete zu entfernen"
    fi
fi

# -- 6. Remove all Wundio files and user
section "6/6  Removing Wundio files and user"

for dir in /opt/wundio /var/lib/wundio /etc/wundio; do
    if [[ -d "$dir" ]]; then
        rm -rf "$dir"
        ok "Removed $dir"
    fi
done

rm -f /var/log/wundio-install.log /var/log/wundio-update.log
rm -f /tmp/wundio-player.json
ok "Logs und Temp-Dateien entfernt"

if id wundio &>/dev/null; then
    userdel wundio 2>/dev/null || true
    ok "User 'wundio' entfernt"
fi

# -- Done
echo ""
echo -e "${GREEN}${BOLD}--------------------------------------------${NC}"
echo -e "${GREEN}${BOLD}  Wundio vollstaendig entfernt.${NC}"
echo -e "${GREEN}${BOLD}--------------------------------------------${NC}"
echo ""
echo -e "  Entfernt:"
echo -e "  - systemd-Dienste gestoppt"
echo -e "  - Port 8000 freigegeben"
echo -e "  - Netzwerk-Konfiguration entfernt"
echo -e "  - Dateien entfernt (/opt/wundio, /var/lib/wundio, /etc/wundio)"
echo -e "  - System-User 'wundio' entfernt"
echo -e "  - Wundio-eigene apt-Pakete entfernt (vorhandene Pakete unveraendert)"
echo ""
echo -e "  Ein Neustart wird empfohlen: ${YELLOW}sudo reboot${NC}"
echo ""