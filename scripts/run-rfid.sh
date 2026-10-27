#!/usr/bin/env bash
# Wundio – RFID Service Runner
# Note: RFID is handled internally by wundio-core (services/rfid.py).
# This script can be used to run RFID diagnostics manually. It uses the
# reader configured via RFID_TYPE (rc522 | pn532 | rfid2) in wundio.env.
#
# Usage: sudo bash scripts/run-rfid.sh

set -euo pipefail

VENV="/opt/wundio/venv"

if [[ ! -f "$VENV/bin/python" ]]; then
    echo "Wundio venv not found at $VENV – run install.sh first"
    exit 1
fi

# wundio-core holds the reader – release it for the duration of the test
RESTART_CORE=false
if systemctl is-active --quiet wundio-core 2>/dev/null; then
    echo "Stopping wundio-core for the test (restarted afterwards)..."
    systemctl stop wundio-core
    RESTART_CORE=true
fi
trap '[[ "$RESTART_CORE" == "true" ]] && systemctl start wundio-core' EXIT

echo "Running RFID diagnostic scan..."
echo "Hold a tag near the reader. Press Ctrl+C to stop."
echo ""

cd /opt/wundio/core
"$VENV/bin/python" - << 'PYEOF' || true
import sys, time

from config import get_settings
from services.rfid import _build_driver_from_config

rfid_type = get_settings().rfid_type
driver = _build_driver_from_config()
if not driver.setup():
    print(f"Reader '{rfid_type}' not found – check wiring and RFID_TYPE in /etc/wundio/wundio.env")
    sys.exit(1)

print(f"Reader '{rfid_type}' ({type(driver).__name__}) ready. Waiting for tag...")
last = None
try:
    while True:
        uid = driver.read_uid_blocking()
        if uid and uid != last:
            print(f"Tag detected: {uid}")
        last = uid
        time.sleep(0.1)
except KeyboardInterrupt:
    pass
finally:
    driver.teardown()
PYEOF
