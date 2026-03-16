#!/usr/bin/env bash
# Wundio – RFID Service Runner
# Note: RFID is handled internally by wundio-core (services/rfid.py).
# This script can be used to run RFID diagnostics manually.
#
# Usage: sudo bash scripts/run-rfid.sh

set -euo pipefail

VENV="/opt/wundio/venv"

if [[ ! -f "$VENV/bin/python" ]]; then
    echo "Wundio venv not found at $VENV – run install.sh first"
    exit 1
fi

echo "Running RFID diagnostic scan..."
echo "Hold a tag near the reader. Press Ctrl+C to stop."
echo ""

cd /opt/wundio/core
"$VENV/bin/python" - << 'PYEOF'
import sys, time, signal

try:
    import RPi.GPIO as GPIO
    from mfrc522 import SimpleMFRC522

    GPIO.setwarnings(False)
    reader = SimpleMFRC522()
    r = reader.READER
    print("RC522 initialised. Waiting for tag...")

    def on_exit(sig, frame):
        GPIO.cleanup()
        sys.exit(0)
    signal.signal(signal.SIGINT, on_exit)

    while True:
        (status, _) = r.MFRC522_Request(r.PICC_REQIDL)
        if status == r.MI_OK:
            (status2, uid) = r.MFRC522_Anticoll()
            if status2 == r.MI_OK:
                uid_str = "".join(f"{b:02X}" for b in uid)
                print(f"Tag detected: {uid_str}")
        time.sleep(0.1)

except ImportError as e:
    print(f"Import error: {e}")
    print("Run: sudo /opt/wundio/venv/bin/pip install mfrc522 RPi.GPIO")
    sys.exit(1)
PYEOF