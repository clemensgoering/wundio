#!/usr/bin/env bash
# Wundio Pull – Update from Git
#
# Pulls latest changes from GitHub and optionally rebuilds the frontend.
# Safe: creates backup before pulling, can rollback on errors.
#
# Usage:
#   wundio-pull              # Pull backend only (fast)
#   wundio-pull --full       # Pull + rebuild frontend
#   wundio-pull --branch dev # Pull from specific branch

set -euo pipefail

REPO_DIR="/opt/wundio"
BACKUP_DIR="/opt/wundio-backups"
WEB_DIR="${REPO_DIR}/web"
STATIC_DIR="${REPO_DIR}/core/static/web"
LOG_FILE="/var/log/wundio-pull.log"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${BLUE}[pull]${NC} $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}   $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; exit 1; }

# ── Argument Parsing ──────────────────────────────────────────────────────────
REBUILD_FRONTEND=false
BRANCH="main"
FORCE_PULL=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full|-f)       REBUILD_FRONTEND=true; shift ;;
        --branch|-b)     BRANCH="$2"; shift 2 ;;
        --force)         FORCE_PULL=true; shift ;;
        --help|-h)
            cat << EOF
Wundio Pull - Update from Git

Usage: wundio-pull [OPTIONS]

Options:
  --full, -f           Pull + rebuild frontend (takes ~5 min on Pi 3)
  --branch, -b <name>  Pull from specific branch (default: main)
  --force              Force pull (discards local changes)
  --help, -h           Show this help

Examples:
  wundio-pull              # Quick backend update
  wundio-pull --full       # Full update with frontend rebuild
  wundio-pull -b dev       # Pull from dev branch
  wundio-pull --force      # Force pull (危险: discards changes)

After pulling, restart the service:
  sudo systemctl restart wundio-core
EOF
            exit 0
            ;;
        *) error "Unknown option: $1 (use --help)" ;;
    esac
done

# ── Checks ────────────────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    error "Must run as root. Use: sudo wundio-pull"
fi

if [[ ! -d "$REPO_DIR/.git" ]]; then
    error "Not a git repository: ${REPO_DIR}"
fi

cd "$REPO_DIR"

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Wundio Pull – Update from Git${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════${NC}"
echo ""

# ── Pre-Pull Info ─────────────────────────────────────────────────────────────
CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

info "Aktueller Stand:"
echo "  Branch:  ${CURRENT_BRANCH}"
echo "  Commit:  ${CURRENT_COMMIT}"
echo "  Repo:    clemensgoering/wundio"
echo ""

# ── Check for local changes ───────────────────────────────────────────────────
if [[ "$FORCE_PULL" == false ]]; then
    if ! git diff-index --quiet HEAD -- 2>/dev/null; then
        warn "Lokale Änderungen gefunden:"
        git status --short
        echo ""
        read -p "  Änderungen verwerfen und fortfahren? (j/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Jj]$ ]]; then
            info "Abgebrochen. Nutze 'git stash' um Änderungen zu sichern."
            exit 0
        fi
        git reset --hard HEAD
        ok "Lokale Änderungen verworfen"
    fi
fi

# ── Create Backup ─────────────────────────────────────────────────────────────
info "Erstelle Backup..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/wundio-${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"

# Backup core (Python) + wundio.env
cp -r "${REPO_DIR}/core" "${BACKUP_PATH}-core" || warn "Core backup fehlgeschlagen"
if [[ -f /etc/wundio/wundio.env ]]; then
    cp /etc/wundio/wundio.env "${BACKUP_PATH}.env" || warn "Env backup fehlgeschlagen"
fi

ok "Backup erstellt: ${BACKUP_PATH}"

# Keep only last 5 backups
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR" | wc -l)
if [[ $BACKUP_COUNT -gt 5 ]]; then
    info "Lösche alte Backups (behalte letzte 5)..."
    ls -t "$BACKUP_DIR" | tail -n +6 | xargs -I {} rm -rf "${BACKUP_DIR}/{}"
fi

# ── Git Pull ──────────────────────────────────────────────────────────────────
info "Wechsle zu Branch: ${BRANCH}"
git fetch origin "$BRANCH" || error "Fetch fehlgeschlagen. Internetverbindung ok?"

if [[ "$CURRENT_BRANCH" != "$BRANCH" ]]; then
    git checkout "$BRANCH" || error "Checkout fehlgeschlagen"
fi

info "Ziehe Updates von GitHub..."
git pull origin "$BRANCH" || {
    error "Pull fehlgeschlagen. Rollback mit: cp -r ${BACKUP_PATH}-core ${REPO_DIR}/core"
}

NEW_COMMIT=$(git rev-parse --short HEAD)

if [[ "$CURRENT_COMMIT" == "$NEW_COMMIT" ]]; then
    ok "Bereits auf dem neuesten Stand (${NEW_COMMIT})"
    CHANGES_PULLED=false
else
    ok "Updates gezogen: ${CURRENT_COMMIT} → ${NEW_COMMIT}"
    CHANGES_PULLED=true
    
    # Show changelog
    echo ""
    info "Änderungen:"
    git log --oneline "${CURRENT_COMMIT}..${NEW_COMMIT}" | head -10
    echo ""
fi

# ── Rebuild Frontend (optional) ───────────────────────────────────────────────
if [[ "$REBUILD_FRONTEND" == true ]]; then
    info "Baue Frontend neu..."
    
    # Detect Pi model for time estimate
    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "Unknown")
    if [[ "$PI_MODEL" == *"Raspberry Pi 3"* ]]; then
        warn "Pi 3 erkannt – Build dauert 5-15 Minuten..."
    elif [[ "$PI_MODEL" == *"Raspberry Pi 4"* ]]; then
        info "Pi 4 erkannt – Build dauert 2-5 Minuten..."
    fi
    
    cd "$WEB_DIR"
    
    # Install dependencies (only if package.json changed)
    if git diff --name-only "${CURRENT_COMMIT}..${NEW_COMMIT}" | grep -q "package.json"; then
        info "package.json geändert – installiere Dependencies..."
        npm install --prefer-offline --no-audit || error "npm install fehlgeschlagen"
    fi
    
    # Build
    info "Starte Vite Build..."
    npm run build || error "Build fehlgeschlagen"

    ok "Frontend neu gebaut (→ ${STATIC_DIR})"

    # Cleanup
    rm -rf node_modules/.cache 2>/dev/null || true

    cd "$REPO_DIR"
fi

# ── Cleanup ───────────────────────────────────────────────────────────────────
if [[ "$REBUILD_FRONTEND" == true ]]; then
    info "Räume auf..."
    rm -rf "${WEB_DIR}/node_modules/.cache" 2>/dev/null || true
    rm -rf "${WEB_DIR}/dist" 2>/dev/null || true
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
ok "Pull erfolgreich abgeschlossen!"
echo ""

if [[ "$CHANGES_PULLED" == true ]] || [[ "$REBUILD_FRONTEND" == true ]]; then
    echo -e "${YELLOW}╔════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  WICHTIG: Service-Neustart erforderlich   ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════╝${NC}"
    echo ""
    echo "  Führe aus:"
    echo -e "  ${BLUE}sudo systemctl restart wundio-core${NC}"
    echo ""
    echo "  Oder für vollständigen Neustart:"
    echo -e "  ${BLUE}sudo reboot${NC}"
    echo ""
else
    info "Keine Änderungen – kein Neustart nötig"
fi

# ── Rollback Info ─────────────────────────────────────────────────────────────
if [[ "$CHANGES_PULLED" == true ]]; then
    echo "Rollback (falls Probleme):"
    echo "  sudo cp -r ${BACKUP_PATH}-core ${REPO_DIR}/core"
    echo "  sudo systemctl restart wundio-core"
    echo ""
fi

echo "Logs: ${LOG_FILE}"
echo ""
