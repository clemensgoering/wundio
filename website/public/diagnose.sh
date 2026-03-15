#!/usr/bin/env bash
# Wundio – Diagnose-Script
# Auf dem Pi ausführen: sudo bash diagnose.sh
# Gibt alle relevanten Infos aus um Verbindungsprobleme zu debuggen

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Wundio Diagnose  $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Netzwerk ──────────────────────────────────────────────────────────────────
echo "[ NETZWERK ]"
echo "  IP-Adressen:"
ip -4 addr show | grep inet | awk '{print "    " $2 " (" $NF ")"}'
echo ""
echo "  WiFi SSID:"
iwgetid wlan0 2>/dev/null || echo "    (nicht verbunden)"
echo ""

# ── Services ──────────────────────────────────────────────────────────────────
echo "[ SERVICES ]"
for svc in wundio-core wundio-rfid wundio-hotspot; do
    STATUS=$(systemctl is-active $svc 2>/dev/null || echo "nicht gefunden")
    ENABLED=$(systemctl is-enabled $svc 2>/dev/null || echo "-")
    echo "  $svc: $STATUS (enabled: $ENABLED)"
done
echo ""

# ── Port ──────────────────────────────────────────────────────────────────────
echo "[ PORT 8000 ]"
if ss -tlnp 2>/dev/null | grep -q ":8000"; then
    echo "  ✓ Port 8000 ist geöffnet"
    ss -tlnp | grep ":8000"
else
    echo "  ✗ Nichts hört auf Port 8000 – wundio-core läuft nicht!"
fi
echo ""

# ── Firewall ──────────────────────────────────────────────────────────────────
echo "[ FIREWALL ]"
if command -v ufw &>/dev/null; then
    ufw status 2>/dev/null | head -5
else
    echo "  ufw nicht installiert (kein Problem)"
fi
iptables -L INPUT -n 2>/dev/null | grep -E "DROP|REJECT" | head -5 || echo "  Keine blockierenden iptables-Regeln"
echo ""

# ── Logs (letzte 20 Zeilen wundio-core) ──────────────────────────────────────
echo "[ WUNDIO-CORE LOG (letzte 20 Zeilen) ]"
journalctl -u wundio-core -n 20 --no-pager 2>/dev/null || echo "  Keine Logs gefunden"
echo ""

# ── Python venv ───────────────────────────────────────────────────────────────
echo "[ PYTHON VENV ]"
VENV="/opt/wundio/venv"
if [[ -f "$VENV/bin/python" ]]; then
    echo "  ✓ venv vorhanden: $VENV"
    "$VENV/bin/python" --version 2>&1 | awk '{print "  Python: " $0}'
    if [[ -f "/opt/wundio/core/main.py" ]]; then
        echo "  ✓ core/main.py vorhanden"
    else
        echo "  ✗ core/main.py fehlt!"
    fi
else
    echo "  ✗ Python venv fehlt unter $VENV"
fi
echo ""

# ── Config ────────────────────────────────────────────────────────────────────
echo "[ KONFIGURATION ]"
[[ -f /etc/wundio/wundio.env ]] && cat /etc/wundio/wundio.env | grep -v PASSWORD || echo "  /etc/wundio/wundio.env nicht gefunden"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Diagnose abgeschlossen"
echo "  Ergebnis teilen: sudo bash diagnose.sh > diagnose.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"