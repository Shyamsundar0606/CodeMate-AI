$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectRoot
try {
    docker info --format '{{.ServerVersion}}' | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Docker Engine is unavailable." }
    $named = @(docker ps -a --filter 'name=^codemate-postgres$' --format '{{.Names}}')
    $owned = @(docker ps -a --filter 'name=^codemate-postgres$' --filter 'label=com.docker.compose.project=codemate-ai' --filter 'label=com.docker.compose.service=postgres' --format '{{.Names}}')
    if ($named.Count -gt 0 -and $owned.Count -eq 0) {
        throw "Container name codemate-postgres belongs to another configuration; left untouched."
    }
    $listeners = @(Get-NetTCPConnection -State Listen -ErrorAction Stop | Where-Object LocalPort -eq 5433)
    $running = @(docker ps --filter 'name=^codemate-postgres$' --filter 'label=com.docker.compose.project=codemate-ai' --filter 'publish=5433' --format '{{.Names}}')
    if ($listeners.Count -gt 0 -and $running.Count -eq 0) {
        throw "Port 5433 is occupied by another service; no resources changed."
    }
    docker compose -p codemate-ai up -d --wait postgres
    if ($LASTEXITCODE -ne 0) { throw "CodeMate PostgreSQL failed to become ready." }
    docker compose -p codemate-ai ps postgres
} finally {
    Pop-Location
}
