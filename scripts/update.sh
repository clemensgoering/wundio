#!/usr/bin/env bash
# Wundio – Update Script
# Updates source, dependencies and restarts services.
# Run: sudo bash /opt/wundio/scripts/update.sh
# Or:  curl -fsSL https://wundio.dev/update.sh | sudo bash

set -euo pipefail

INSTALL_DIR="/opt/wundio"
VENV_DIR="${INSTALL_DIR}/venv"
GIT_BRANCH="${WUNDIO_BRANCH:-main}"
LOG_FILE="/var/log/wundio-update.log"

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

info()    { echo -e "${BLUE}[INFO]${NC}  $*" | tee -a "$LOG_FILE"; }
ok()      { echo -e "${GREEN}[ OK ]${NC}  $*" | tee -a "$LOG_FILE"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error()   { echo -e "${RED}[ERR ]${NC}  $*" | tee -a "$LOG_FILE"; exit 1; }
section() {
    echo "" | tee -a "$LOG_FILE"
    echo -e "${BOLD}${CYAN}━━━  $*  ━━━${NC}" | tee -a "$LOG_FILE"
}

# ── Spinner ───────────────────────────────────────────────────────────────────
_spin_frames=("⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏")
spin_bg() {
    local label="$1"
    local i=0
    while true; do
        printf "\r  ${CYAN}${_spin_frames[$i]}${NC}  %s..." "$label" >&2
        i=$(( (i+1) % ${#_spin_frames[@]} ))
        sleep 0.12
    done
}

run_spin() {
    local label="$1"; shift
    spin_bg "$label" &
    local SPIN_PID=$!
    set +e
    "$@" >> "$LOG_FILE" 2>&1
    local EXIT_CODE=$?
    set -e
    kill $SPIN_PID 2>/dev/null; wait $SPIN_PID 2>/dev/null || true
    printf "\r  %-60s\n" "" >&2
    if [[ $EXIT_CODE -eq 0 ]]; then
        ok "$label"
    else
        error "$label failed (exit $EXIT_CODE) – see $LOG_FILE"
    fi
    return $EXIT_CODE
}

# ── Checks ────────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Run as root: sudo bash update.sh"
[[ ! -d "$INSTALL_DIR/.git" ]] && error "No installation found at $INSTALL_DIR. Run install.sh first."

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== Wundio update $(date) ===" >> "$LOG_FILE"

echo -e "${BOLD}"
echo "  Wundio Updater – wundio.dev"
echo -e "${NC}"

# ── Show current version ──────────────────────────────────────────────────────
CURRENT_COMMIT=$(git -C "$INSTALL_DIR" rev-parse --short HEAD 2>/dev/null || echo "unknown")
info "Current version: $CURRENT_COMMIT on branch $GIT_BRANCH"

# ── 1. Check for changes upstream ─────────────────────────────────────────────
section "1/5  Checking for updates"
run_spin "git fetch" git -C "$INSTALL_DIR" fetch origin "$GIT_BRANCH"

LOCAL=$(git  -C "$INSTALL_DIR" rev-parse HEAD)
REMOTE=$(git -C "$INSTALL_DIR" rev-parse "origin/$GIT_BRANCH")

if [[ "$LOCAL" == "$REMOTE" ]]; then
    ok "Already up to date – nothing to do."
    echo ""
    systemctl is-active wundio-core &>/dev/null && \
        info "Services running. Use --force to reinstall anyway." || \
        warn "Services not running. Starting them now..."
    systemctl start wundio-rfid wundio-core 2>/dev/null || true
    exit 0
fi

CHANGES=$(git -C "$INSTALL_DIR" log --oneline HEAD..origin/"$GIT_BRANCH" 2>/dev/null | head -10)
info "Updates available:"
echo "$CHANGES" | while IFS= read -r line; do
    echo "    ${CYAN}→${NC} $line"
done

# ── 2. Stop services ──────────────────────────────────────────────────────────
section "2/5  Stopping services"
systemctl stop wundio-core  2>/dev/null && ok "wundio-core stopped"  || warn "wundio-core was not running"
systemctl stop wundio-rfid  2>/dev/null && ok "wundio-rfid stopped"  || warn "wundio-rfid was not running"

# ── 3. Pull latest source ─────────────────────────────────────────────────────
section "3/5  Pulling latest source"
run_spin "git pull" git -C "$INSTALL_DIR" pull origin "$GIT_BRANCH"

NEW_COMMIT=$(git -C "$INSTALL_DIR" rev-parse --short HEAD)
ok "Updated: $CURRENT_COMMIT → $NEW_COMMIT"

# ── 4. Update Python dependencies ────────────────────────────────────────────
section "4/5  Updating Python packages"
info "Checking for new or changed dependencies..."

run_spin "pip update" "$VENV_DIR/bin/pip" install \
    --upgrade \
    --prefer-binary \
    --quiet \
    -r "$INSTALL_DIR/core/requirements.txt"

# Reload systemd units in case they changed
cp "$INSTALL_DIR/systemd/"*.service /etc/systemd/system/ 2>/dev/null || true
systemctl daemon-reload

# ── 5. Restart services ───────────────────────────────────────────────────────
section "5/5  Restarting services"
run_spin "start wundio-rfid" systemctl start wundio-rfid

# Wait until core is actually ready, not just started
info "Starting wundio-core..."
systemctl start wundio-core
for i in $(seq 1 15); do
    sleep 1
    if systemctl is-active --quiet wundio-core; then
        ok "wundio-core is running"
        break
    fi
    printf "\r  ${CYAN}⠙${NC}  Waiting for wundio-core... (%ds)" "$i" >&2
done
printf "\r  %-60s\n" "" >&2

if ! systemctl is-active --quiet wundio-core; then
    error "wundio-core failed to start – check: sudo journalctl -u wundio-core -n 30"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}${BOLD}  ✓  Wundio updated successfully!${NC}"
echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Version:  ${CYAN}$CURRENT_COMMIT${NC} → ${GREEN}$NEW_COMMIT${NC}"
echo -e "  Log:      $LOG_FILE"
echo ""
systemctl status wundio-core --no-pager -l | head -8