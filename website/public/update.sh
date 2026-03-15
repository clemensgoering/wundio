#!/usr/bin/env bash
# Wundio – Update Script
# Updates source, dependencies and restarts services.
# Run: sudo bash /opt/wundio/scripts/update.sh

set -euo pipefail

INSTALL_DIR="/opt/wundio"
VENV_DIR="${INSTALL_DIR}/venv"
GIT_BRANCH="${WUNDIO_BRANCH:-main}"

RED='\033[0;31m'; GREEN='\033[0;32m'; BLUE='\033[0;34m'; BOLD='\033[1m'; NC='\033[0m'
info()  { echo -e "${BLUE}[update]${NC} $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }
error() { echo -e "${RED}[error]${NC} $*"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash update.sh"
[[ ! -d "$INSTALL_DIR/.git" ]] && error "No git repo at $INSTALL_DIR. Did you install via install.sh?"

info "Stopping services..."
systemctl stop wundio-core wundio-rfid 2>/dev/null || true

info "Pulling latest $GIT_BRANCH..."
git -C "$INSTALL_DIR" fetch origin
git -C "$INSTALL_DIR" checkout "$GIT_BRANCH"
git -C "$INSTALL_DIR" pull origin "$GIT_BRANCH"

info "Updating Python dependencies..."
"$VENV_DIR/bin/pip" install --upgrade -r "$INSTALL_DIR/core/requirements.txt" -q

info "Reloading systemd units..."
cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload

info "Restarting services..."
systemctl start wundio-rfid
sleep 2
systemctl start wundio-core

ok "Wundio updated and running."
systemctl status wundio-core --no-pager -l | head -15
