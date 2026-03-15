#!/usr/bin/env bash
# Wundio – First-run WiFi Hotspot Setup
# Creates a temporary AP so users can configure home WiFi via browser.
# Triggered on install or when wifi_configured=false in the database.
#
# Uses hostapd + dnsmasq. Captive-portal redirect is optional.

set -euo pipefail

CONF_DIR="/etc/wundio"
HOTSPOT_SSID="${HOTSPOT_SSID:-Wundio-Setup}"
HOTSPOT_PASSWORD="${HOTSPOT_PASSWORD:-wundio123}"
HOTSPOT_IP="${HOTSPOT_IP:-192.168.50.1}"
IFACE="${WUNDIO_IFACE:-wlan0}"

# Load env if available
[[ -f "$CONF_DIR/wundio.env" ]] && source "$CONF_DIR/wundio.env"

info() { echo "[hotspot] $*"; }

# ── hostapd config ────────────────────────────────────────────────────────────
cat > /etc/hostapd/wundio-hostapd.conf << EOF
interface=${IFACE}
driver=nl80211
ssid=${HOTSPOT_SSID}
hw_mode=g
channel=7
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=${HOTSPOT_PASSWORD}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP
rsn_pairwise=CCMP
EOF

# ── dnsmasq config ────────────────────────────────────────────────────────────
cat > /etc/dnsmasq.d/wundio-hotspot.conf << EOF
# Wundio Hotspot DHCP
interface=${IFACE}
bind-dynamic
domain-needed
bogus-priv
dhcp-range=192.168.50.10,192.168.50.50,255.255.255.0,12h
dhcp-option=3,${HOTSPOT_IP}
dhcp-option=6,${HOTSPOT_IP}
# Captive portal: redirect all DNS to our IP
address=/#/${HOTSPOT_IP}
EOF

# ── systemd service for hotspot ───────────────────────────────────────────────
cat > /etc/systemd/system/wundio-hotspot.service << EOF
[Unit]
Description=Wundio WiFi Hotspot
After=network.target
Before=wundio-core.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStartPre=/sbin/ip addr add ${HOTSPOT_IP}/24 dev ${IFACE} || true
ExecStartPre=/sbin/ip link set ${IFACE} up
ExecStart=/usr/sbin/hostapd /etc/hostapd/wundio-hostapd.conf -B
ExecStartPost=/bin/systemctl restart dnsmasq
ExecStop=/bin/pkill hostapd || true
ExecStop=/sbin/ip addr del ${HOTSPOT_IP}/24 dev ${IFACE} || true

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable wundio-hotspot
systemctl start wundio-hotspot || true

info "Hotspot '${HOTSPOT_SSID}' configured on ${IFACE} → ${HOTSPOT_IP}"
info "Users connect to WiFi '${HOTSPOT_SSID}' and open http://${HOTSPOT_IP}:8000"
