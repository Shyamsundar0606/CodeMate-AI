# Trusted application deployment and local demonstration

This guide concerns CodeMate's trusted application services. Hostile repository
execution remains disabled. No worker, launcher, privileged socket, execution
queue or patch application is deployed by these instructions.

## Configuration inventory

| Profile | Settings and intended use |
| --- | --- |
| Development | APP_ENV=development, generated ignored local secrets, localhost frontend/API, Secure cookie off for local HTTP only |
| Automated test | APP_ENV=test, guarded codemate_test_user/codemate_test_db on 127.0.0.1:5433; controlled GitHub/Ollama; ephemeral JWT signing key |
| Controlled portfolio verification | Production Next.js build plus isolated test API/account and controlled upstream evidence; never a public production deployment |
| Production design | APP_ENV=production, Secure cookies, explicit HTTPS origins, independent random JWT/database/GitHub encryption secrets, TLS ingress and private services |

backend/.env.production.example contains deliberately invalid placeholders. Never
copy it over an existing .env or commit filled values. Provision secrets through a
service manager/secret manager. Generate independent high-entropy keys privately;
do not print them in logs, screenshots, shell transcripts or verification reports.
Production rejects placeholder signing/database credentials and the dedicated test
database identity. Missing signing/database settings fail validation. GitHub
requires its client ID/secret and independent Fernet key together, with HTTPS
callback/frontend URLs in production. Existing settings validators remain active.

Public frontend configuration contains only NEXT_PUBLIC_API_URL. Build it for the
actual public origin, without credentials, query or fragment. Never put GitHub,
JWT, database or model credentials into NEXT_PUBLIC variables. Existing .env files
and speech/model files remain ignored. The new production example alone is unignored.

## Service and resource boundaries

| Service | Exposure and lifecycle |
| --- | --- |
| PostgreSQL | Existing codemate-postgres, loopback 5433, dedicated persistent volume and non-superuser application role; no public database port |
| API | Loopback 8000 by default; one process, at most 32 concurrent requests, backlog 128, five-second keep-alive, 20-second graceful shutdown deadline |
| Frontend | Loopback 3000 for demo; production build, existing Next.js runtime, no development HMR in portfolio verification |
| Ollama | Existing loopback 11434 only, optional local qwen2.5-coder:3b; never a public endpoint or startup dependency |
| Voice | Existing lazy bounded STT/TTS subprocesses with local model paths; typed navigation remains available without microphone/models |
| AI investigation worker | Optional separate trusted process; existing finite retries, owner/job locks and model deadlines; no sandbox execution |

Start Docker Desktop and the existing ownership/port-guarded PostgreSQL helper.
Apply additive migrations with alembic upgrade head; current head stays
0006_sandbox_previews. Never recreate the database or remove its volume to deploy.
Back up and test restore before real production changes; backup automation and a
restore drill were not implemented or verified in Milestone 11.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure/start-postgres.ps1
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic check
Set-Location ..
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure/start-api.ps1
```

The API helper uses --no-proxy-headers and --no-access-log. It does not stop an
existing listener, disable Windows security or start optional models. Use Ctrl+C
in the terminal you started. For an additional owned verification process, its
Port parameter allows a separate free loopback port. It never exposes 0.0.0.0.

In separate terminals:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd ci
npm.cmd run build
npm.cmd start -- --port 3000
```

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
# Only when existing AI investigations are needed:
.\.venv\Scripts\python.exe scripts/ai_worker.py
# Check the existing Ollama service without downloading a model:
# ollama list
# Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

## TLS and reverse proxy design

Public TLS deployment is designed, not provisioned or verified on this Windows
machine. A reviewed TLS ingress must terminate HTTPS, enforce body/connection
budgets and route to private loopback application services. Use same-site HTTPS
frontend/API origins for Strict cookies. Configure GitHub's exact authorized
callback URL. Do not expose PostgreSQL, Ollama or Docker management through ingress.

Default API startup ignores all forwarded identity headers. If a real deployment
needs client-IP forwarding for accurate IP throttling, permit only explicitly
trusted proxy peers through Uvicorn's forwarded-allow-ips and network controls.
The proxy must replace, rather than append to, untrusted X-Forwarded-For, and
strip alternate identity headers. Never set forwarded-allow-ips to a wildcard.
Direct requests must not bypass the proxy. Otherwise the safe no-forwarding
default groups clients behind a proxy into one IP throttle bucket; account-level
limits still apply. No forwarded-header trust is silently enabled by application
settings. Terminate TLS at the reviewed ingress and configure HSTS there for the
frontend. The API adds HSTS only under APP_ENV=production.

Ingress must allow bounded voice uploads while keeping ordinary JSON small.
The API caps ordinary bodies at HTTP_MAX_BODY_BYTES (default 1 MiB) and raw voice
transcription at the existing VOICE_MAX_UPLOAD_BYTES (default 8 MiB). Reads of a
body have a shared HTTP_BODY_TIMEOUT_SECONDS budget (default 15 seconds); streamed
requests cannot bypass the byte limit. This budget is separate from bounded model
inference deadlines. The example command's concurrency cap also bounds the total
number of buffered uploads. The ingress should use compatible or stricter limits.

The frontend baseline CSP restricts network origins, frames, objects and resources.
It permits inline script/style for Next hydration; it is not a nonce-based strict
XSS policy. unsafe-eval is allowed only for development HMR, not production builds.
Microphone permission remains self-only for the voice page. JSON API production
responses use default-src none; production API docs/OpenAPI are disabled. Live
public TLS, a nonce-based CSP rollout and external penetration testing remain work.

## Observability and operational checks

GET /health is process liveness only. GET /health/ready checks PostgreSQL and
migration 0006, without model inference. Failure returns sanitized unavailable/503;
recovery becomes ready/200. Engine bounds remain five pooled plus five overflow
connections, ten-second pool wait, five-second connect and ten-second statement
timeout, pre-ping and a new 30-minute recycle interval. Probe deadlines at ingress
must account for these bounds; this is not a subsecond database-outage guarantee.
Sessions close per request and roll back on errors. Optional Ollama/voice failure
does not make the entire API unready.

Application logs are JSON with UTC timestamp, severity, service/environment,
server request ID, validated UUID correlation ID, route template, method, status
and measured duration. Unknown paths become unmatched. Bodies, raw URL paths,
queries, cookies, headers, prompts, transcripts and exception tracebacks are not
serialized by the application formatter. Upstream access-log filters remain.
Do not install a duplicate root handler that re-emits raw application messages.
Use the API helper's disabled Uvicorn access log to avoid duplicate request logs.
Configure restricted log retention/rotation in the deployment log collector.

GET /api/v1/operations/metrics is JSON, requires a valid active ADMIN bearer token,
and is no-store. Do not place tokens in URLs or enable a public scrape bypass.
It exposes per-process route-template/method/status-class counts, cumulative
duration buckets and authorization/readiness/sandbox-denial counters. There are
no raw user, email, repository, prompt or correlation-ID labels. Values reset on
restart and are not aggregated across processes. This is not a Prometheus service
or full distributed tracing. Alerts/retention dashboards need operator setup.

The browser displays a validated request ID for failed HTTP responses. That ID
and client correlation metadata assist diagnosis; neither is authorization or
idempotency proof. Existing request-body UUIDs continue to deduplicate mutations.
API ai_queued logs link the HTTP context to an investigation UUID; the existing
AI worker uses that UUID as its processing correlation ID. No new private source
or original HTTP context is persisted in the database.

## Reproducible portfolio verification

With the venv, node_modules and Edge already installed, free ports 3000/8001 and
no concurrent backend suite:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure/verify-demo.ps1
# After a current production build, avoid rebuilding:
# powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure/verify-demo.ps1 -UseExistingBuild
```

The wrapper invokes the existing controlled browser fixture with real Next.js,
FastAPI and the guarded test database. It creates a unique disposable account and
random password, never prints a universal credential, exercises authorized source,
CI evidence, explanation/proposal/review, exact preview, six blockers, disabled
Run, cancellation/history and safe voice navigation, then cleans only its owned
account/child servers. It refuses occupied ports. Screenshots stay ignored.
The headless controlled profile is portfolio verification, not an interactive
public deployment or proof of real-model repair quality. Personal GitHub and real
Ollama can be demonstrated separately with deliberately authorized repositories.

## Bounded performance measurements

Run one benchmark phase at a time against the guarded test DB, never concurrently
with pytest/browser verification. It measures trusted application code only:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
$env:CODEMATE_BENCHMARK_PHASE = 'hardened'
.\.venv\Scripts\python.exe -m pytest tests/benchmark_demo.py -q -W error --tb=line
Remove-Item Env:CODEMATE_BENCHMARK_PHASE
```

The benchmark records 20 warmed GET samples per operation, nearest-rank p95, a
single controlled AI explanation and Python tracemalloc peak. It uses in-process
TestClient, real guarded PostgreSQL and mocked GitHub/model responses. It is not
network/internet, throughput, cold Ollama or whole-process RSS evidence. The saved
baseline was measured before core changes. Re-running baseline on hardened code
would overwrite that historical artifact and is not a valid before measurement.
Do not claim percentage speedups from these small local runs.

## Release limitations

This milestone does not certify public production readiness. Remaining work
includes real TLS/ingress verification, backups/restore, monitoring operations,
external security review, nonce-based CSP, deployment resource sizing and the
documented development-tooling advisories. Already issued stateless access JWTs
remain valid for up to their configured lifetime after logout; refresh tokens
are revoked immediately. Account deactivation is checked on protected requests.
Pattern redaction and finite tests do not prove absence of every unknown secret.
All six sandbox admission blockers and SANDBOX_UNVERIFIED remain release invariants.
