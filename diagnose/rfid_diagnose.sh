#!/usr/bin/env bash
# Wundio – RFID Diagnose
# Ausfuehren: sudo bash rfid_diagnose.sh

set -euo pipefail
LOG=/tmp/rfid_diagnose.log
echo "=== RFID Diagnose $(date) ===" | tee $LOG

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; NC='\033[0m'
ok()   { echo -e "${GREEN}[OK]${NC}   $*" | tee -a $LOG; }
fail() { echo -e "${RED}[FAIL]${NC} $*" | tee -a $LOG; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a $LOG; }
info() { echo -e "${BLUE}[INFO]${NC} $*" | tee -a $LOG; }

echo ""
info "--- 1. SPI aktiviert? ---"
if lsmod | grep -q spi_bcm2835; then
    ok "spi_bcm2835 geladen"
else
    fail "spi_bcm2835 fehlt – Fix: sudo raspi-config nonint do_spi 0 && sudo reboot"
fi
[ -e /dev/spidev0.0 ] && ok "/dev/spidev0.0 vorhanden" || fail "/dev/spidev0.0 fehlt"

echo ""
info "--- 2. Gruppen ---"
groups wundio 2>/dev/null | grep -q spi  && ok "wundio in Gruppe spi"  || fail "wundio fehlt in Gruppe spi  – Fix: sudo usermod -aG spi wundio && sudo reboot"
groups wundio 2>/dev/null | grep -q gpio && ok "wundio in Gruppe gpio" || fail "wundio fehlt in Gruppe gpio – Fix: sudo usermod -aG gpio wundio && sudo reboot"

echo ""
info "--- 3. Python-Pakete ---"
VENV=/opt/wundio/venv
$VENV/bin/python -c "import mfrc522; print('  ok')" 2>/dev/null && ok "mfrc522" || fail "mfrc522 fehlt"
$VENV/bin/python -c "import RPi.GPIO"                2>/dev/null && ok "RPi.GPIO" || fail "RPi.GPIO fehlt"
$VENV/bin/python -c "import spidev"                  2>/dev/null && ok "spidev"   || fail "spidev fehlt"

echo ""
info "--- 4. Service ---"
[ "$(systemctl is-active wundio-core)" = "active" ] && ok "wundio-core laeuft" || fail "wundio-core nicht aktiv"

echo ""
info "--- 5. RFID-Log ---"
journalctl -u wundio-core --no-pager -n 30 2>/dev/null \
    | grep -iE "rfid|spi|mfrc|scan|error" | tail -20 \
    | while IFS= read -r line; do echo "  $line"; done

echo ""
info "--- 6. Direkttest (Karte auflegen wenn bereit) ---"
echo "Enter druecken um zu starten..."
read -r

$VENV/bin/python3 - << 'PYEOF'
import sys, time, signal
print("Initialisiere RC522...")
try:
    import RPi.GPIO as GPIO
    from mfrc522 import SimpleMFRC522

    GPIO.setwarnings(False)
    r = SimpleMFRC522()
    reader = r.READER

    print("Bereit. Karte auflegen... (10s Timeout)")

    def on_timeout(sig, frame):
        print("\nTimeout – keine Karte erkannt.")
        print("Pruefe:")
        print("  1. Kabel: SDA->Pin24, SCK->Pin23, MOSI->Pin19, MISO->Pin21, RST->Pin22, 3.3V->Pin1, GND->Pin6")
        print("  2. Versorgung: RC522 an 3.3V (NICHT 5V!)")
        GPIO.cleanup()
        sys.exit(1)
    signal.signal(signal.SIGALRM, on_timeout)
    signal.alarm(10)

    while True:
        (status, _) = reader.Request(reader.PICC_REQIDL)
        if status == reader.MI_OK:
            (status2, uid) = reader.Anticoll()
            if status2 == reader.MI_OK:
                uid_str = "".join(f"{b:02X}" for b in uid)
                print(f"\nKarte erkannt! UID: {uid_str}")
                print("RFID funktioniert korrekt.")
                break
        time.sleep(0.1)

    signal.alarm(0)
    GPIO.cleanup()

except ImportError as e:
    print(f"Import-Fehler: {e}")
except Exception as e:
    print(f"Fehler: {e}")
    print("Moegliche Ursache: falsche Verkabelung oder RC522 an 5V statt 3.3V")
PYEOF

echo ""
echo "Log: $LOG"