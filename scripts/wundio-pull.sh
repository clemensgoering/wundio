#!/usr/bin/env bash
# Wundio Pull - Update from Git
#
# Usage:
#   wundio-pull              # Pull backend only (fast)
#   wundio-pull --full       # Pull + rebuild frontend
#   wundio-pull --branch dev # Pull from specific branch
#   wundio-pull --force      # Discard local changes without prompting

set -euo pipefail

REPO_DIR="/opt/wundio"
BACKUP_DIR="/opt/wundio-backups"
WEB_DIR="${REPO_DIR}/web"
STATIC_DIR="${REPO_DIR}/core/static/web"
LOG_FILE="/var/log/wundio-pull.log"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; RED='\033[0;31m'; NC='\033[0m'

info()  { echo -e "${BLUE}[pull]${NC} $*" | tee -a "$LOG_FILE"; }
ok()    { echo -e "${GREEN}[ OK ]${NC}   $*" | tee -a "$LOG_FILE"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*" | tee -a "$LOG_FILE"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "$LOG_FILE"; exit 1; }

# ── Argument Parsing ──────────────────────────────────────────────────────────
REBUILD_FRONTEND=false
BRANCH="main"
FORCE_PULL=false
NON_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --full|-f)         REBUILD_FRONTEND=true; shift ;;
        --branch|-b)       BRANCH="$2"; shift 2 ;;
        --force)           FORCE_PULL=true; shift ;;
        --non-interactive) NON_INTERACTIVE=true; FORCE_PULL=true; shift ;;
        --help|-h)
            cat << EOF
Wundio Pull - Update from Git

Usage: wundio-pull [OPTIONS]

Options:
  --full, -f           Pull + rebuild frontend (takes ~5 min on Pi 3)
  --branch, -b <name>  Pull from specific branch (default: main)
  --force              Discard local changes without prompting
  --non-interactive    For UI/scripted use: never prompt, implies --force
  --help, -h           Show this help
EOF
            exit 0
            ;;
        *) error "Unknown option: $1 (use --help)" ;;
    esac
done

# ── Auto-detect non-interactive (no TTY = called from web UI) ─────────────────
if [[ ! -t 0 ]]; then
    NON_INTERACTIVE=true
    FORCE_PULL=true
fi

# ── Checks ────────────────────────────────────────────────────────────────────
[[ $EUID -ne 0 ]] && error "Must run as root. Use: sudo wundio-pull"
[[ ! -d "$REPO_DIR/.git" ]] && error "Not a git repository: ${REPO_DIR}"

mkdir -p "$(dirname "$LOG_FILE")"
echo "=== wundio-pull $(date) ===" >> "$LOG_FILE"

cd "$REPO_DIR"

# Ensure fileMode is disabled – running as root causes permission bit
# differences that make every file appear modified.
git config core.fileMode false

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo "==============================================="
echo "  Wundio Pull - Update from Git"
echo "==============================================="
echo ""

CURRENT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

info "Aktueller Stand:"
echo "  Branch:  ${CURRENT_BRANCH}"
echo "  Commit:  ${CURRENT_COMMIT}"
echo "  Repo:    clemensgoering/wundio"
echo ""

# ── Handle local changes ──────────────────────────────────────────────────────
# Exclude core/static/ from the check (build output, not source)
CHANGED=$(git diff-index --name-only HEAD -- 2>/dev/null \
    | grep -v '^core/static/' || true)
UNTRACKED=$(git ls-files --others --exclude-standard \
    | grep -v '^core/static/' || true)

HAS_CHANGES=false
if [[ -n "$CHANGED" ]] || [[ -n "$UNTRACKED" ]]; then
    HAS_CHANGES=true
fi

if [[ "$HAS_CHANGES" == true ]]; then
    warn "Lokale Aenderungen gefunden:"
    [[ -n "$CHANGED" ]]   && echo "$CHANGED" | sed 's/^/ M /'
    [[ -n "$UNTRACKED" ]] && echo "$UNTRACKED" | sed 's/^/ ? /'
    echo ""

    if [[ "$FORCE_PULL" == true ]]; then
        info "--force aktiv: Verwerfe lokale Aenderungen..."
        git reset --hard HEAD
        git clean -fd --exclude=core/static/ >> "$LOG_FILE" 2>&1
        ok "Lokale Aenderungen verworfen"
    elif [[ "$NON_INTERACTIVE" == false ]]; then
        read -p "  Aenderungen verwerfen und fortfahren? (j/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Jj]$ ]]; then
            info "Abgebrochen. Nutze --force um automatisch zu verwerfen."
            exit 0
        fi
        git reset --hard HEAD
        git clean -fd --exclude=core/static/ >> "$LOG_FILE" 2>&1
        ok "Lokale Aenderungen verworfen"
    fi
fi

# ── Backup ────────────────────────────────────────────────────────────────────
info "Erstelle Backup..."
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_PATH="${BACKUP_DIR}/wundio-${TIMESTAMP}"
mkdir -p "$BACKUP_DIR"
cp -r "${REPO_DIR}/core" "${BACKUP_PATH}-core" || warn "Core backup fehlgeschlagen"
[[ -f /etc/wundio/wundio.env ]] && \
    cp /etc/wundio/wundio.env "${BACKUP_PATH}.env" || warn "Env backup fehlgeschlagen"
ok "Backup: ${BACKUP_PATH}"

# Keep last 5 backups
ls -t "$BACKUP_DIR" | tail -n +6 | xargs -I {} rm -rf "${BACKUP_DIR}/{}" 2>/dev/null || true

# ── Git Pull ──────────────────────────────────────────────────────────────────
info "Fetch origin/${BRANCH}..."
git fetch origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE" \
    || error "Fetch fehlgeschlagen. Internetverbindung ok?"

[[ "$CURRENT_BRANCH" != "$BRANCH" ]] && git checkout "$BRANCH"

info "Ziehe Updates..."
git pull origin "$BRANCH" 2>&1 | tee -a "$LOG_FILE" \
    || error "Pull fehlgeschlagen."

NEW_COMMIT=$(git rev-parse --short HEAD)
CHANGES_PULLED=false
if [[ "$CURRENT_COMMIT" != "$NEW_COMMIT" ]]; then
    ok "Updates gezogen: ${CURRENT_COMMIT} -> ${NEW_COMMIT}"
    CHANGES_PULLED=true
    echo ""
    info "Aenderungen:"
    git log --oneline "${CURRENT_COMMIT}..${NEW_COMMIT}" | head -10
    echo ""
else
    ok "Bereits aktuell (${NEW_COMMIT})"
fi


# ── Restore script permissions & normalize git index ────────────────────────
# Restore permissions and suppress false M entries for all scripts
chmod +x "$REPO_DIR"/scripts/*.sh
chmod +x "$REPO_DIR"/diagnose/*.sh 2>/dev/null || true
git ls-files scripts/ diagnose/ \
    | xargs -r git update-index --assume-unchanged
ok "Script-Berechtigungen wiederhergestellt"

if [[ "$REBUILD_FRONTEND" == true ]]; then
    info "Baue Frontend neu..."

    PI_MODEL=$(cat /proc/device-tree/model 2>/dev/null | tr -d '\0' || echo "")
    [[ "$PI_MODEL" == *"Raspberry Pi 3"* ]] && \
        warn "Pi 3 erkannt - Build dauert 5-15 Minuten..."
    [[ "$PI_MODEL" == *"Raspberry Pi 4"* ]] && \
        info "Pi 4 erkannt - Build dauert 2-5 Minuten..."

    cd "$WEB_DIR"

    # Only reinstall if package.json changed
    if [[ "$CHANGES_PULLED" == true ]] && \
       git diff --name-only "${CURRENT_COMMIT}..${NEW_COMMIT}" | grep -q "package.json"; then
        info "package.json geaendert - installiere Dependencies..."
        npm install --prefer-offline --no-audit 2>&1 | tee -a "$LOG_FILE" \
            || error "npm install fehlgeschlagen"
    fi

    npm run build 2>&1 | tee -a "$LOG_FILE" || error "Build fehlgeschlagen"
    ok "Frontend gebaut -> ${STATIC_DIR}"

    rm -rf node_modules/.cache 2>/dev/null || true
    cd "$REPO_DIR"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
ok "Pull abgeschlossen!"
echo ""

if [[ "$CHANGES_PULLED" == true ]] || [[ "$REBUILD_FRONTEND" == true ]]; then
    echo "  -> Neustart erforderlich:"
    echo "     sudo systemctl restart wundio-core"
    echo ""
    echo "  Rollback falls noetig:"
    echo "     sudo cp -r ${BACKUP_PATH}-core ${REPO_DIR}/core"
    echo "     sudo systemctl restart wundio-core"
fi

echo "  Log: ${LOG_FILE}"
echo ""