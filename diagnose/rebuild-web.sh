#!/usr/bin/env bash
# Web-UI neu bauen und Service neu starten
set -euo pipefail

# Fix ownership so the wundio user can write to the build output dir
mkdir -p /opt/wundio/core/static/web
chown -R wundio:wundio /opt/wundio/core/static/web
chown -R wundio:wundio /opt/wundio/web

echo "Building Web UI..."
cd /opt/wundio/web
sudo -u wundio npm run build

echo "Restarting wundio-core..."
systemctl restart wundio-core

echo "Done. Open http://wundio.local:8000"