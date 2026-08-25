#!/usr/bin/env bash
# ==============================================================================
# QCMS Enterprise Production Deployment & Automated Rollback Engine
# Architecture: Zero-Downtime Rolling Build -> Health Check -> Auto-Rollback
# ==============================================================================

set -eo pipefail

# --- Color Constants ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Logging Helpers ---
log_info()    { echo -e "${CYAN}[QCMS-DEPLOY]${NC} $1"; }
log_success() { echo -e "${GREEN}[QCMS-DEPLOY ✅]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[QCMS-DEPLOY ⚠️]${NC} $1"; }
log_error()   { echo -e "${RED}[QCMS-DEPLOY ❌]${NC} $1"; }
log_stage()   { echo -e "\n${PURPLE}======================================================================${NC}\n${BLUE}[QCMS STAGE]${NC} $1\n${PURPLE}======================================================================${NC}"; }

START_TIME=$(date +%s)
DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEPLOY_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

# Detect docker compose CLI command
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose -f $COMPOSE_FILE"
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose -f $COMPOSE_FILE"
else
    log_error "Neither 'docker compose' nor 'docker-compose' is installed on this host."
    exit 1
fi

# Target Git branch
BRANCH="${1:-main}"

# State files for rollback
STATE_DIR="$DEPLOY_DIR/.deploy_state"
mkdir -p "$STATE_DIR"
PREV_COMMIT_FILE="$STATE_DIR/prev_stable_commit"
PREV_TAG_FILE="$STATE_DIR/prev_stable_tag"

log_stage "1/6: Capturing Pre-Deployment Snapshot & Stable Baseline"

# Record current working commit before pulling
if git rev-parse --verify HEAD >/dev/null 2>&1; then
    PREV_COMMIT=$(git rev-parse HEAD)
    echo "$PREV_COMMIT" > "$PREV_COMMIT_FILE"
    log_info "Recorded baseline stable commit: ${YELLOW}$PREV_COMMIT${NC}"
else
    PREV_COMMIT=""
fi

# Tag current running images as 'stable' for instant rollback capability
if docker image inspect qcms-backend:latest >/dev/null 2>&1; then
    docker tag qcms-backend:latest qcms-backend:stable 2>/dev/null || true
    log_info "Tagged current backend image as 'qcms-backend:stable'"
fi
if docker image inspect qcms-frontend:latest >/dev/null 2>&1; then
    docker tag qcms-frontend:latest qcms-frontend:stable 2>/dev/null || true
    log_info "Tagged current frontend image as 'qcms-frontend:stable'"
fi

# ==============================================================================
# Rollback Function Definition
# ==============================================================================
rollback() {
    local EXIT_CODE=$?
    log_error "Deployment step failed (Exit Code: $EXIT_CODE)! Initiating AUTOMATIC ROLLBACK..."
    
    log_stage "EMERGENCY ROLLBACK IN PROGRESS"

    # Dump diagnostic logs
    log_warn "Fetching last 40 lines of container logs for failure diagnosis:"
    $DOCKER_COMPOSE logs --tail=40 || true

    # Revert Git Repository if previous commit is available
    if [ -n "$PREV_COMMIT" ]; then
        log_info "Reverting Git repository to previous stable commit: ${YELLOW}$PREV_COMMIT${NC}..."
        git fetch --all 2>/dev/null || true
        git reset --hard "$PREV_COMMIT" || true
    fi

    # Attempt to restore stable containers
    log_info "Restoring previous stable container images..."
    if docker image inspect qcms-backend:stable >/dev/null 2>&1 && docker image inspect qcms-frontend:stable >/dev/null 2>&1; then
        docker tag qcms-backend:stable qcms-backend:latest || true
        docker tag qcms-frontend:stable qcms-frontend:latest || true
        $DOCKER_COMPOSE up -d --no-build --remove-orphans || true
    else
        log_warn "Rebuilding previous stable commit directly..."
        $DOCKER_COMPOSE up -d --build --remove-orphans || true
    fi

    # Verify Rollback Health
    log_info "Verifying rollback health status..."
    sleep 5
    if bash "$DEPLOY_DIR/scripts/healthcheck.sh" >/dev/null 2>&1; then
        log_success "Rollback successful! Previous stable version is alive and healthy."
    else
        log_error "Rollback health check failed! Manual operator intervention required immediately."
    fi

    ELAPSED=$(( $(date +%s) - START_TIME ))
    log_error "Deployment aborted and rolled back in ${ELAPSED}s."
    exit 1
}

# Trap any unexpected error, interrupt, or termination signal to trigger rollback
trap rollback ERR SIGINT SIGTERM

log_stage "2/6: Fetching Newest Release & Updating Working Tree"
log_info "Fetching latest code from remote for branch: ${GREEN}$BRANCH${NC}..."
git fetch --all --prune
git checkout "$BRANCH"
git reset --hard "origin/$BRANCH"
NEW_COMMIT=$(git rev-parse HEAD)
log_success "Working tree updated to target commit: ${GREEN}$NEW_COMMIT${NC}"

log_stage "3/6: Non-Destructive Container Build (Keep Old Traffic Serving)"
log_info "Building new container images in background (Zero-Downtime)..."
$DOCKER_COMPOSE build --pull

log_stage "4/6: Seamless Service Update & Container Swap"
log_info "Launching updated containers (rolling replacement)..."
$DOCKER_COMPOSE up -d --remove-orphans

log_stage "5/6: Automated Deep Health Check Verification Loop"
log_info "Starting health probe validation (Backend API, DB, Redis, Frontend)..."

HEALTH_PASSED=false
MAX_RETRIES=15
RETRY_INTERVAL=4

for (( i=1; i<=MAX_RETRIES; i++ )); do
    log_info "Health Probe Attempt $i/$MAX_RETRIES..."
    if bash "$DEPLOY_DIR/scripts/healthcheck.sh"; then
        HEALTH_PASSED=true
        break
    fi
    sleep $RETRY_INTERVAL
done

if [ "$HEALTH_PASSED" != "true" ]; then
    log_error "Health checks failed after $MAX_RETRIES attempts!"
    false # Triggers ERR trap -> rollback()
fi

log_stage "6/6: Finalizing Deployment & Tagging Stable Release"

# Tag newly verified images as stable
docker tag qcms-backend:latest qcms-backend:stable 2>/dev/null || true
docker tag qcms-frontend:latest qcms-frontend:stable 2>/dev/null || true
echo "$NEW_COMMIT" > "$PREV_COMMIT_FILE"

# Clean up dangling images to keep host disk space tidy
log_info "Pruning unused dangling container image layers..."
docker image prune -f --filter "until=24h" >/dev/null 2>&1 || true

ELAPSED=$(( $(date +%s) - START_TIME ))
log_success "QCMS Enterprise Deployment completed successfully in ${ELAPSED}s!"
log_success "Active Commit: $NEW_COMMIT"
log_success "Services: Backend (Port 5000) & Frontend (Port 80) are HEALTHY."
exit 0
