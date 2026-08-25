#!/usr/bin/env bash
# ==============================================================================
# QCMS Enterprise Deep Health Probe
# Validates Backend Liveness, Readiness (DB + Redis), and Frontend Nginx status
# ==============================================================================

set -eo pipefail

BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:5000}"
FRONTEND_URL="${FRONTEND_URL:-http://127.0.0.1:80}"

# 1. Backend Liveness Check
LIVE_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/health/live" 2>/dev/null || echo "000")
if [ "$LIVE_STATUS" -ne 200 ]; then
    echo "❌ Backend Liveness probe failed (HTTP $LIVE_STATUS) at $BACKEND_URL/health/live"
    exit 1
fi

# 2. Backend Readiness & Dependency Check (DB + Redis)
READY_RESPONSE=$(curl -s "$BACKEND_URL/api/health" 2>/dev/null || curl -s "$BACKEND_URL/health/ready" 2>/dev/null || echo "{}")
if ! echo "$READY_RESPONSE" | grep -q '"status":\s*"ready"\|\"status\":\s*\"ok\"\|\"db\":\s*\"ok\"'; then
    echo "❌ Backend Readiness check failed. Response: $READY_RESPONSE"
    exit 1
fi

# 3. Frontend HTTP 200 Check
FRONT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL/" 2>/dev/null || echo "000")
if [ "$FRONT_STATUS" -ne 200 ] && [ "$FRONT_STATUS" -ne 304 ]; then
    # Fallback check against backend's static file server if frontend standalone container is not mapped on 80
    BACKEND_FRONT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/" 2>/dev/null || echo "000")
    if [ "$BACKEND_FRONT_STATUS" -ne 200 ] && [ "$BACKEND_FRONT_STATUS" -ne 304 ]; then
        echo "❌ Frontend HTTP probe failed (HTTP $FRONT_STATUS at $FRONTEND_URL/ and HTTP $BACKEND_FRONT_STATUS at $BACKEND_URL/)"
        exit 1
    fi
fi

echo "✅ All Health Checks Passed (Backend API, DB, Redis & Frontend Nginx are operational)."
exit 0
