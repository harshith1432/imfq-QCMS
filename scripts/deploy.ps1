# ==============================================================================
# QCMS Enterprise Windows / PowerShell Deployment & Automated Rollback Script
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"
$StartTime = Get-Date

Write-Host "======================================================================" -ForegroundColor Magenta
Write-Host "[QCMS-DEPLOY] Starting Deployment & Rollback Engine on Branch: $Branch" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Magenta

$DeployDir = Split-Path -Parent $PSScriptRoot
Set-Location $DeployDir

$ComposeFile = "docker-compose.prod.yml"
if (-not (Test-Path $ComposeFile)) {
    $ComposeFile = "docker-compose.yml"
}

$StateDir = Join-Path $DeployDir ".deploy_state"
if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir | Out-Null }
$PrevCommitFile = Join-Path $StateDir "prev_stable_commit"

# 1. Snapshot previous stable commit
$PrevCommit = ""
try {
    $PrevCommit = (git rev-parse HEAD).Trim()
    Set-Content -Path $PrevCommitFile -Value $PrevCommit
    Write-Host "[QCMS-DEPLOY] Baseline stable commit: $PrevCommit" -ForegroundColor Yellow
} catch {}

# Tag existing images as stable
try {
    docker tag qcms-backend:latest qcms-backend:stable 2>$null
    docker tag qcms-frontend:latest qcms-frontend:stable 2>$null
} catch {}

function Invoke-Rollback {
    param([string]$Reason)
    Write-Host "`n[QCMS-DEPLOY ❌] Deployment Failure: $Reason" -ForegroundColor Red
    Write-Host "[QCMS-DEPLOY ⚠️] INITIATING AUTOMATIC ROLLBACK..." -ForegroundColor Yellow

    if ($PrevCommit) {
        Write-Host "[QCMS-DEPLOY] Resetting Git to: $PrevCommit..." -ForegroundColor Yellow
        git fetch --all 2>$null
        git reset --hard $PrevCommit
    }

    Write-Host "[QCMS-DEPLOY] Restoring previous stable containers..." -ForegroundColor Yellow
    try {
        docker compose -f $ComposeFile up -d --build --remove-orphans
    } catch {
        docker-compose -f $ComposeFile up -d --build --remove-orphans
    }

    Write-Host "[QCMS-DEPLOY ✅] Rollback completed." -ForegroundColor Green
    exit 1
}

# 2. Pull latest changes
try {
    Write-Host "[QCMS-DEPLOY] Fetching latest changes..." -ForegroundColor Cyan
    git fetch --all --prune
    git checkout $Branch
    git reset --hard "origin/$Branch"
} catch {
    Invoke-Rollback "Failed to update Git branch: $_"
}

# 3. Build containers
try {
    Write-Host "[QCMS-DEPLOY] Building containers..." -ForegroundColor Cyan
    docker compose -f $ComposeFile build
} catch {
    Invoke-Rollback "Docker build failed: $_"
}

# 4. Start containers
try {
    Write-Host "[QCMS-DEPLOY] Starting containers..." -ForegroundColor Cyan
    docker compose -f $ComposeFile up -d --remove-orphans
} catch {
    Invoke-Rollback "Docker startup failed: $_"
}

# 5. Health check loop
Write-Host "[QCMS-DEPLOY] Verifying health checks..." -ForegroundColor Cyan
$HealthPassed = $false
for ($i = 1; $i -le 12; $i++) {
    Start-Sleep -Seconds 4
    try {
        $live = Invoke-RestMethod -Uri "http://127.0.0.1:5000/health/live" -TimeoutSec 3 -ErrorAction SilentlyContinue
        $ready = Invoke-RestMethod -Uri "http://127.0.0.1:5000/api/health" -TimeoutSec 3 -ErrorAction SilentlyContinue
        if ($live.status -eq "ok" -and ($ready.status -eq "ready" -or $ready.db -eq "ok")) {
            $HealthPassed = $true
            break
        }
    } catch {}
    Write-Host "  Health check probe attempt $i/12..." -ForegroundColor Gray
}

if (-not $HealthPassed) {
    Invoke-Rollback "Health check probes timed out or failed readiness verification!"
}

# 6. Finalize
try {
    docker tag qcms-backend:latest qcms-backend:stable 2>$null
    docker tag qcms-frontend:latest qcms-frontend:stable 2>$null
    docker image prune -f 2>$null
} catch {}

$Elapsed = [math]::Round(((Get-Date) - $StartTime).TotalSeconds)
Write-Host "[QCMS-DEPLOY ✅] Deployment Succeeded in ${Elapsed}s!" -ForegroundColor Green
