param([ValidateRange(1024, 65535)][int]$Port = 8000)

$ErrorActionPreference = 'Stop'
$apiRoot = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $apiRoot 'backend')
try {
    # Trusted application service only. No reload, forwarding trust or runtime control.
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port $Port --no-proxy-headers --no-access-log --workers 1 --limit-concurrency 32 --backlog 128 --timeout-keep-alive 5 --timeout-graceful-shutdown 20
    if ($LASTEXITCODE -ne 0) { throw 'API stopped unsuccessfully; inspect the sanitized service logs' }
} finally {
    Pop-Location
}
