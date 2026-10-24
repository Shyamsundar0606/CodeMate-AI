# Milestone 11 verification

Verified locally on 2026-10-23, Windows, Python 3.12.10, Next.js 16.4.2.
Scope: trusted application production hardening and a controlled local demo.
Sandbox execution remains disabled. Public production readiness is not certified.

## A. Implementation summary

Started from clean main 6ff3715014858b00615c5cd81c552668a930d092 and created
feature/milestone-11-production-hardening. Audited authentication, database,
GitHub/Ollama/voice, CI, deployment and the six blocked runner requirements first.
Selected small additions around existing bounded services rather than a rewrite.
Added request protection, sanitized observability, protected metrics, production
configuration checks, headers and reproducible Windows demo/startup helpers.

## B. Architecture and security

Pure ASGI protection wraps CORS and routes, including preflight/errors. Ordinary
bodies default to 1 MiB, voice transcription retains 8 MiB, and body reads share
a 15-second deadline. Both declared and actual streamed lengths are checked.
Invalid lengths return 400, oversize 413 and slow uploads 408. Ready chunks cannot
bypass the total deadline. Bodies are buffered within the limit, not streamed
unboundedly. Concurrency must also be bounded by the server/ingress.

Responses add nosniff, DENY, no-referrer and restrictive permissions headers.
API/health are no-store. Production API adds HSTS and default-src none CSP and
disables docs/OpenAPI. Production settings reject placeholder signing/database
secrets, the dedicated test database identity and wildcard/control-character CORS
origins. Existing HTTPS/Secure cookie validation, Argon2/JWT, CSRF, refresh rotation,
owner/RBAC authorization, throttling and read-only GitHub boundaries remain.

Threat model now explicitly includes slow uploads, raw-path/log injection,
correlation spoofing, metrics identity leakage and proxy header spoofing. IDs are
diagnostic metadata, never authentication. The API helper ignores forwarded
headers and disables duplicate raw Uvicorn access logging. Public proxy trust
must be explicitly configured for actual ingress peers; no wildcard trust.

The six blockers remain worker identity, launcher separation, image provenance,
hostile-code isolation, durable recovery and approved patch integration. The
unchanged backend denies a valid execution confirmation with 503
SANDBOX_UNVERIFIED after authorization/hash checks. Capability/schema flags stay
false and the UI Run remains disabled. No executor, executable queue, runtime
control endpoint, repository code execution, patch application, Docker privilege,
socket/mount or insecure execution fallback was added. Migration remains 0006.

## C. Structured logging and correlation

JSON contains UTC timestamp, severity, service/environment, validated IDs and
allowlisted event fields. HTTP events include route template, bounded method,
status and measured duration. Unknown paths become unmatched. Server request IDs
are freshly generated UUIDv4; client correlation IDs must be canonical UUIDv4.
ContextVar isolation is tested with concurrent requests. API queue events link
the context to the existing investigation UUID; the separate trusted AI worker
uses that UUID as processing correlation. No new private context is persisted.

Formatter excludes bodies, raw paths/queries, tokens/cookies, prompts/transcripts,
freeform exception text and tracebacks. Existing upstream URL filtering remains.
Restricted collection, retention/rotation and avoiding duplicate raw root handlers
remain operator duties. Pattern-based protection and tests are not proof against
every future secret or third-party logger. Streaming failures after headers have
already been sent cannot retroactively change the client's HTTP status.

## D. Metrics and health

GET /api/v1/operations/metrics requires an active ADMIN bearer token and is
no-store. Lock-protected in-process aggregates expose route-template/method/status
class counts, duration sums and cumulative buckets at 5, 25, 100, 500, 2000,
10000 ms and infinity. Events count authorization denial, readiness failure and
sandbox confirmation denial. No user, email, repository, prompt or ID labels.
Counters reset on restart; there is no distributed metrics store or Prometheus
integration. Dashboards, alerts and retention are not provisioned.

/health is liveness; /health/ready checks PostgreSQL and migration version.
Database failure returns sanitized 503 and recovery returns 200. Optional model
or voice unavailability does not make the whole API unready. Existing connection
and pool deadlines apply; this is not a subsecond outage guarantee.

## E. Database and AI reliability

Retained five pooled plus five overflow connections, ten-second pool wait,
five-second connect, ten-second statement timeout, pre-ping and request session
rollback/close. Added 1800-second pool recycling. No migration/dependency changes.
Existing finite AI retries/job ownership, cancellation, schema/source/citation
validation and bounded Ollama/GitHub clients remain covered by the full suite.
No speculative retry, model call on readiness or unrestricted cache was added.
Public GitHub and real Ollama outages/inference quality were not tested live.

## F. Frontend performance and accessibility

The sandbox panel reuses one capability-schema parse per render. Mutation
idempotency UUID behavior is unchanged. Failed requests show a validated server
request ID for support; each request sends a fresh correlation UUID. Baseline CSP
restricts origins, objects and framing; development alone permits unsafe-eval.
Inline script/style remain allowed for Next hydration, so this is not strict
nonce-based XSS prevention. Voice retains self microphone permission. Existing
keyboard/labeled controls and regression tests remain. Production Edge demo at
390-pixel width had no overflow or page errors; no full WCAG certification claimed.

## G. Actual benchmark results

Same Windows/Python environment, real guarded test PostgreSQL, in-process
TestClient, controlled GitHub/model fixtures, source 32 bytes. Each GET has one
warmup and 20 timed samples; p95 uses nearest rank. Baseline saved before core
hardening; final hardened artifact refreshed after the final middleware change.

| Operation | Baseline median / p95 ms | Hardened median / p95 ms | Samples each |
| --- | --- | --- | --- |
| Health | 4.985 / 5.480 | 4.859 / 6.166 | 20 |
| Authenticated account | 16.362 / 17.658 | 14.018 / 15.616 | 20 |
| GitHub repository listing | 23.484 / 26.401 | 22.920 / 24.496 | 20 |
| Automation history | 17.743 / 18.882 | 17.351 / 18.408 | 20 |
| Execution preview read | 32.213 / 40.093 | 31.535 / 32.702 | 20 |

Single controlled AI explanation: baseline 98.993 ms, hardened 96.795 ms; no p95
for one sample. Python tracemalloc peak: 594951 versus 572171 bytes, not process
RSS. Production build elapsed 24.72 seconds locally. These are small local runs,
not causal speedup, load capacity, real-model latency or internet throughput
evidence. Health p95 increased in the final sample; no universal improvement is
claimed. Raw artifacts and the explicit opt-in benchmark are allowlisted below.

## H. Deployment and local demo

DEPLOYMENT.md and WINDOWS.md provide exact PowerShell commands, configuration
profiles, service boundaries and TLS/reverse-proxy design. start-api.ps1 binds
127.0.0.1, one worker, concurrency 32, backlog 128, five-second keepalive and
20-second graceful shutdown. The production example deliberately fails validation
until independently generated real secrets are provisioned. Existing .env and
personal resources are untouched.

Both new PowerShell files pass parser checks. An owned API process using the same
startup flags passed liveness/readiness/header smoke checks and was stopped.
verify-demo.ps1 -UseExistingBuild passed using real production Next.js/FastAPI,
guarded fixture PostgreSQL and headless Microsoft Edge. Controlled GitHub/Ollama
exercised source, evidence, explanation, proposal/review, rejection, preview,
six blockers, cancellation/history and voice navigation. Result: executionRequests
0, pageErrors 0, mobileOverflow false. Mobile screenshot visually inspected.
Fixture accounts/child servers were cleaned by the existing owned-resource helper;
screenshots remain ignored. No public TLS deployment or real-model demo claimed.

## I. Regression and static verification

| Check | Actual local result |
| --- | --- |
| Full backend pytest -q -W error --tb=line | 562 passed, 238.01 seconds |
| Final controlled benchmark | 1 passed, 4.39 seconds, separate opt-in run |
| Ruff lint | Passed |
| Ruff formatting | 125 files already formatted |
| Alembic heads/current | 0006_sandbox_previews |
| Alembic check | No new upgrade operations |
| pip check | Passed |
| Frontend Vitest | 175 passed across 11 files |
| ESLint, TypeScript | Passed |
| Next.js 16.4.2 production build | Passed |
| Controlled preparation browser verification | Passed |

New backend cases cover JSON redaction, concurrent correlation isolation, spoofed
headers, unknown raw paths, safe 500/errors/preflight, body/voice limits, malformed
lengths, timeout including ready chunks, protected private metrics, DB failure and
recovery, production settings/headers/docs. Existing sandbox denial regressions
remain part of the full suite. CI was inspected: pinned actions, read-only contents,
no persisted checkout credential, dependency caching/locked installs, guarded
PostgreSQL, warnings-as-errors, lint/format, migration and frontend production build.
No personal credentials, physical microphone, GPU, Ollama or hostile-code Docker
job is required. Hosted GitHub Actions was not run from this local task. No CI
workflow change or broader artifact-retention pipeline was introduced.

## J. Dependency audit

No dependency pins changed. Next.js and eslint-config-next remain 16.4.2 with
matching existing package lock. Isolated pip-audit: 85 pinned packages, zero
known findings; pip check passed. Production npm audit: zero vulnerabilities.
Full npm audit retains five existing high development-tooling findings through
braces/micromatch/fast-glob/Next ESLint tooling. These are open, not waived as clean.
Python lockfiles pin versions but do not yet enforce hashes for every artifact.
Audits are point-in-time advisory checks, not comprehensive exploit certification.

## K. Unresolved limitations

No public TLS/ingress, production backup/restore drill, external penetration test,
distributed telemetry, strict nonce CSP or production load sizing was verified.
Already issued stateless access JWTs remain valid up to their configured lifetime
after logout; refresh revocation is immediate and active account checks remain.
Dev-tool advisories, unknown image vulnerability/provenance and all six runner
blockers remain. Docker hostile-isolation fixtures were not rerun for this trusted
application-only milestone; prior fixture success cannot enable execution.

## L. Exact changed files

The 29 paths in section M are the complete intended modified/untracked inventory,
including this report. Generated .next, test screenshots, caches, venv/node_modules,
model files and populated environment files are excluded. frontend/next-env.d.ts
and frontend/AGENTS.md are not part of this change. No personal data or real
credential is intentionally included; tests/examples use controlled dummy values.

## M. Exact staging allowlist

This is a review allowlist, not authorization to stage automatically. Stage only
these 29 exact paths after reviewing their then-current contents:

```text
.gitignore
README.md
backend/.env.production.example
backend/app/ai/worker.py
backend/app/api/routes/operations.py
backend/app/core/config.py
backend/app/core/logging.py
backend/app/core/observability.py
backend/app/db/session.py
backend/app/main.py
backend/app/services/ai_investigation_service.py
backend/scripts/ai_worker.py
backend/tests/benchmark_demo.py
backend/tests/test_operations.py
backend/tests/test_security_config.py
docs/ARCHITECTURE.md
docs/DEPLOYMENT.md
docs/MILESTONE_11_VERIFICATION.md
docs/PROGRESS.md
docs/WINDOWS.md
docs/milestone-11-benchmark-baseline.json
docs/milestone-11-benchmark-hardened.json
frontend/next.config.ts
frontend/src/components/automation/sandbox-panel.tsx
frontend/src/lib/api/client.ts
frontend/src/tests/api.test.ts
frontend/src/tests/build-config.test.ts
infrastructure/start-api.ps1
infrastructure/verify-demo.ps1
```

## N. Git status and preservation

Branch: feature/milestone-11-production-hardening. HEAD remains
6ff3715014858b00615c5cd81c552668a930d092. Index remains empty; no staging, commit,
push, merge, reset or branch deletion. Four existing stash objects remain:

```text
3fce76236a951bc34c86aea3c2ec42a651677fd9
3ddb4687fae40b8a95cceb0b0f5666d21ba954ac
e38d863d98bab479bb87e0978764f9fcc2c1c18c
26b23eadaed05d3865e308f4dc9e45e4441156e1
```

No populated .env, personal/model file, unrelated container or database volume was
replaced. Existing guarded PostgreSQL was started for authorized verification.
Final git diff --check passed. Expanded tracked/untracked inventory exactly matches
the 29-path allowlist, with no missing or unexpected paths. The index is empty.
Credential-signature scan found no private keys, GitHub tokens, AWS access keys or
JWT values in these files. Manual review confirmed intentionally invalid example
credentials and controlled test values. No scan proves absence of unknown secrets.
frontend/next-env.d.ts has no diff and frontend/AGENTS.md does not exist. Newly
created documentation contains no em dash characters. Four stash hashes match
the initial inventory exactly.

## O. Readiness assessment

Ready for review as trusted application hardening with verified local controlled
demo evidence and explicit limitations. This is not a public production readiness
certificate or completion of the isolated execution runner. All execution gates
stay disabled. No Milestone 12 work was started.
