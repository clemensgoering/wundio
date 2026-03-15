#!/usr/bin/env bash
# Wundio - WiFi Hotspot Setup
#
# Intelligentes Verhalten:
#   - Pi bereits im Heimnetz verbunden -> kein Hotspot, direktes Setup über lokale IP
#   - Pi nicht verbunden -> Hotspot erstellen für Erstkonfiguration
#
# Bookworm-kompatibel: funktioniert mit NetworkManager und dhcpcd.

set -euo pipefail

CONF_DIR="/etc/wundio"
HOTSPOT_SSID="${HOTSPOT_SSID:-Wundio-Setup}"
HOTSPOT_PASSWORD="${HOTSPOT_PASSWORD:-wundio123}"
HOTSPOT_IP="${HOTSPOT_IP:-192.168.50.1}"
IFACE="${WUNDIO_IFACE:-wlan0}"
LOG_FILE="/var/log/wundio-install.log"

# Colors
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
info() { echo -e "${BLUE}[hotspot]${NC} $*" | tee -a "$LOG_FILE"; }
ok()   { echo -e "${GREEN}[ OK ]${NC}   $*" | tee -a "$LOG_FILE"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }

# Load env if available
[[ -f "$CONF_DIR/wundio.env" ]] && source "$CONF_DIR/wundio.env" 2>/dev/null || true

# -- Check: already connected to a WiFi network?
_already_connected() {
    # Method 1: iw / iwgetid
    if command -v iwgetid &>/dev/null; then
        iwgetid "$IFACE" --raw 2>/dev/null | grep -q . && return 0
    fi
    # Method 2: ip addr has an IP on wlan0
    ip addr show "$IFACE" 2>/dev/null | grep -q "inet " && return 0
    # Method 3: NetworkManager
    if command -v nmcli &>/dev/null; then
        nmcli -t -f DEVICE,STATE dev 2>/dev/null | grep -q "^${IFACE}:connected" && return 0
    fi
    return 1
}

_get_local_ip() {
    ip -4 addr show "$IFACE" 2>/dev/null \
        | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -1
}

# -- Case A: already connected
if _already_connected; then
    LOCAL_IP=$(_get_local_ip)
    info "Pi is already connected to a WiFi network."
    info "Skipping hotspot - marking WiFi as configured."

    # Mark configured in wundio settings file (DB will be updated by wundio-core on startup)
    if [[ -f "$CONF_DIR/wundio.env" ]]; then
        # Update or append wifi_configured flag
        if grep -q "^WIFI_CONFIGURED=" "$CONF_DIR/wundio.env" 2>/dev/null; then
            sed -i "s/^WIFI_CONFIGURED=.*/WIFI_CONFIGURED=true/" "$CONF_DIR/wundio.env"
        else
            echo "WIFI_CONFIGURED=true" >> "$CONF_DIR/wundio.env"
        fi
    fi

    # Disable hotspot service so it doesn't interfere on reboot
    systemctl disable wundio-hotspot 2>/dev/null || true

    echo ""
    echo -e "${GREEN}--------------------------------------------${NC}"
    echo -e "${GREEN}  WiFi already configured - no hotspot needed${NC}"
    echo -e "${GREEN}--------------------------------------------${NC}"
    echo ""
    if [[ -n "${LOCAL_IP:-}" ]]; then
        echo -e "  Open Wundio in your browser:"
        echo -e "  ${YELLOW}http://${LOCAL_IP}:8000${NC}"
        echo ""
        echo -e "  Or after reboot: ${YELLOW}http://wundio.local:8000${NC}"
    else
        echo -e "  After reboot, open: ${YELLOW}http://wundio.local:8000${NC}"
    fi
    echo ""
    ok "WiFi setup complete (existing network)"
    exit 0
fi

# -- Case B: not connected -> create hotspot
info "No WiFi connection found - setting up hotspot..."

# -- Disable whatever currently manages wlan0

# NetworkManager (Bookworm default on desktop, sometimes on Lite too)
if command -v nmcli &>/dev/null; then
    info "Stopping NetworkManager on $IFACE..."
    nmcli dev set "$IFACE" managed no 2>/dev/null || true
fi

# dhcpcd
if systemctl is-active --quiet dhcpcd 2>/dev/null; then
    info "Stopping dhcpcd..."
    systemctl stop dhcpcd 2>/dev/null || true
fi

# wpa_supplicant - must be stopped so hostapd can claim wlan0
info "Stopping wpa_supplicant..."
systemctl stop wpa_supplicant 2>/dev/null || true
pkill wpa_supplicant 2>/dev/null || true
sleep 1

# Bring interface up clean
ip link set "$IFACE" up 2>/dev/null || true
ip addr flush dev "$IFACE"  2>/dev/null || true

# -- hostapd config
mkdir -p /etc/hostapd
cat > /etc/hostapd/wundio-hostapd.conf << EOF
interface=${IFACE}
driver=nl80211
ssid=${HOTSPOT_SSID}
hw_mode=g
channel=6
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=${HOTSPOT_PASSWORD}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

# Unblock rfkill if needed
rfkill unblock wifi 2>/dev/null || true

# -- dnsmasq config
cat > /etc/dnsmasq.d/wundio-hotspot.conf << EOF
interface=${IFACE}
bind-dynamic
domain-needed
bogus-priv
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,12h
dhcp-option=3,${HOTSPOT_IP}
dhcp-option=6,${HOTSPOT_IP}
# Captive portal redirect
address=/#/${HOTSPOT_IP}
EOF

# -- systemd service
cat > /etc/systemd/system/wundio-hotspot.service << EOF
[Unit]
Description=Wundio WiFi Hotspot
After=network.target
Before=wundio-core.service
# Only run if not already connected to a WiFi network
ConditionPathExists=!/var/lib/wundio/.wifi_configured

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=-/bin/systemctl stop wpa_supplicant
ExecStartPre=-/usr/bin/pkill wpa_supplicant
ExecStartPre=/sbin/ip addr flush dev ${IFACE}
ExecStartPre=/sbin/ip addr add ${HOTSPOT_IP}/24 dev ${IFACE}
ExecStartPre=/sbin/ip link set ${IFACE} up
ExecStart=/usr/sbin/hostapd /etc/hostapd/wundio-hostapd.conf -B
ExecStartPost=/bin/systemctl restart dnsmasq
ExecStop=/bin/pkill hostapd || true
ExecStop=/sbin/ip addr flush dev ${IFACE} || true
ExecStop=-/bin/systemctl start wpa_supplicant

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wundio-hotspot

# Try to start immediately (will work after reboot even if it fails now)
if systemctl start wundio-hotspot 2>/dev/null; then
    ok "Hotspot started successfully"
else
    warn "Hotspot will activate after reboot (interface may still be claimed by network manager)"
fi

info "Hotspot SSID: '${HOTSPOT_SSID}'  Password: '${HOTSPOT_PASSWORD}'"
info "Web interface: http://${HOTSPOT_IP}:8000"

echo ""
echo -e "${GREEN}--------------------------------------------${NC}"
echo -e "${GREEN}  Hotspot configured - reboot to activate${NC}"
echo -e "${GREEN}--------------------------------------------${NC}"
echo ""
echo -e "  After reboot, connect to WiFi:"
echo -e "  Network:  ${YELLOW}${HOTSPOT_SSID}${NC}"
echo -e "  Password: ${YELLOW}${HOTSPOT_PASSWORD}${NC}"
echo -e "  Browser:  ${YELLOW}http://${HOTSPOT_IP}:8000${NC}"
echo ""