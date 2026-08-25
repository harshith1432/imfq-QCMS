#!/usr/bin/env bash
# ==============================================================================
# QCMS Enterprise Manual Emergency Rollback Utility
# Usage: ./scripts/rollback.sh [target_commit_sha]
# ==============================================================================

set -eo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${CYAN}[QCMS-ROLLBACK]${NC} $1"; }
log_success() { echo -e "${GREEN}[QCMS-ROLLBACK ✅]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[QCMS-ROLLBACK ⚠️]${NC} $1"; }
log_error()   { echo -e "${RED}[QCMS-ROLLBACK ❌]${NC} $1"; }

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DEPLOY_DIR"

COMPOSE_FILE="docker-compose.prod.yml"
if [ ! -f "$COMPOSE_FILE" ]; then
    COMPOSE_FILE="docker-compose.yml"
fi

if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose -f $COMPOSE_FILE"
else
    DOCKER_COMPOSE="docker-compose -f $COMPOSE_FILE"
fi

STATE_DIR="$DEPLOY_DIR/.deploy_state"
PREV_COMMIT_FILE="$STATE_DIR/prev_stable_commit"

TARGET_COMMIT="$1"
if [ -z "$TARGET_COMMIT" ] && [ -f "$PREV_COMMIT_FILE" ]; then
    TARGET_COMMIT=$(cat "$PREV_COMMIT_FILE")
fi

log_warn "Initiating Rollback for QCMS Enterprise..."

if [ -n "$TARGET_COMMIT" ]; then
    log_info "Reverting Git working directory to commit: ${YELLOW}$TARGET_COMMIT${NC}..."
    git fetch --all 2>/dev/null || true
    git reset --hard "$TARGET_COMMIT"
fi

if docker image inspect qcms-backend:stable >/dev/null 2>&1 && docker image inspect qcms-frontend:stable >/dev/null 2>&1; then
    log_info "Restoring cached :stable container images..."
    docker tag qcms-backend:stable qcms-backend:latest
    docker tag qcms-frontend:stable qcms-frontend:latest
    $DOCKER_COMPOSE up -d --no-build --remove-orphans
else
    log_info "Rebuilding previous container images from source..."
    $DOCKER_COMPOSE up -d --build --remove-orphans
fi

log_info "Verifying health post-rollback..."
sleep 4
if bash "$DEPLOY_DIR/scripts/healthcheck.sh"; then
    log_success "Rollback completed and system is healthy."
    exit 0
else
    log_error "System health check failed post-rollback. Inspect container logs:"
    $DOCKER_COMPOSE logs --tail=50
    exit 1
fi
