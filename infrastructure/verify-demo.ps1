param([switch]$UseExistingBuild)

$ErrorActionPreference = 'Stop'
$demoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $demoRoot
try {
    # Ownership and port checks live in the existing helper. No prune or volume removal.
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'start-postgres.ps1')
    if ($LASTEXITCODE -ne 0) { throw 'CodeMate PostgreSQL prerequisite failed' }
    Push-Location (Join-Path $demoRoot 'frontend')
    try {
        if ($UseExistingBuild) {
            if (-not (Test-Path -LiteralPath '.next/BUILD_ID')) { throw 'Build frontend first' }
        } else {
            & npm.cmd run build
            if ($LASTEXITCODE -ne 0) { throw 'Production frontend build failed' }
        }
        # Refuses occupied ports. Creates unique disposable accounts without printing passwords.
        & node scripts/verify-automation-browser.mjs
        if ($LASTEXITCODE -ne 0) { throw 'Controlled demonstration verification failed' }
    } finally {
        Pop-Location
    }
} finally {
    Pop-Location
}
