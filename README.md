# CodeMate AI

Autonomous Developer & DevOps Voice Agent. **Milestones 1-3 complete; Milestone 4
implemented, live GitHub verification pending.** The authenticated Next.js workspace
now supports a secure read-only GitHub App connection, repository activity, GitHub
Actions monitoring and bounded job logs through FastAPI/PostgreSQL.

GitHub App registration and live credentials require manual setup. Until configured,
the connection page explains the setup requirement. No live OAuth success is claimed.
See [GitHub setup and security](docs/GITHUB_INTEGRATION.md),
[actual verification results](docs/PROGRESS.md) and [Windows commands](docs/WINDOWS.md).
AI, Ollama, voice and autonomous repository changes remain future milestones.

## Quick start — Windows PowerShell

Python 3.12, Docker Engine/Compose, and Node.js 22.12+ or 24+ are required
for the full frontend test toolchain. Verified locally:
Python 3.12.10, Docker Engine 29.6.2, Compose 5.3.1, Node 24.17.0.
Start Docker Desktop before running database commands.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
# Only if the environment does not already exist:
# py -3.12 -m venv backend\.venv
.\backend\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.lock.txt
.\backend\.venv\Scripts\python.exe backend\scripts\setup_local.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\infrastructure\start-postgres.ps1
Set-Location backend
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --no-proxy-headers
```

The startup helper checks port 5433 and refuses to change an unrelated service.
The execution-policy option applies only to that child PowerShell process.
Local secrets are generated into ignored files, never printed. Existing settings
are preserved. The local environment helper requires python-dotenv, included in
the installed settings dependencies. Blank existing keys are deliberately not
replaced; fill them securely if configuration validation reports missing values.

In another terminal:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd ci
# Only when .env.local does not exist:
# Copy-Item .env.example .env.local
npm.cmd run dev
```

Frontend: http://localhost:3000. API docs: http://localhost:8000/docs.
`GET /health` preserves the original liveness contract.
`GET /health/ready` checks database access and the current migration revision.
The public landing page reports API availability without requiring authentication.
Protected pages hide account content until the API verifies the session. Ollama is not required.
Use localhost consistently for browser URLs and the configured API origin.

## Database isolation

| Setting | CodeMate |
| --- | --- |
| Compose project / container | codemate-ai / codemate-postgres |
| Image | postgres:16-alpine |
| Host binding | **127.0.0.1:5433** to container 5432 |
| Development database / role | codemate_db / codemate_user |
| Test database / role | codemate_test_db / codemate_test_user |
| Persistent volume | codemate-ai-postgres-data |
| Alembic head | 0002_github_integration |

VoxHire's port 5432 and all of its resources remain untouched. Development and test
roles have different generated passwords, own their own databases, and cannot
connect to the other database. The application role is not a PostgreSQL superuser. A separate codemate_owner
bootstrap role has an independent local password and is never used by the API.
Both CodeMate databases share the dedicated local server; no additional test port
is published. Init scripts run only for an empty dedicated volume. Changing .env
passwords does not change passwords in an already initialized database.
Do not remove the persistent volume to apply configuration changes.

Stop only CodeMate, retaining its data:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI'
docker compose -p codemate-ai stop postgres
```

Never use pruning commands or `down -v` for this setup.

## Authentication API

| Method and path | Access |
| --- | --- |
| POST /api/v1/auth/register | Public; X-CodeMate-Request: 1 |
| POST /api/v1/auth/login | Public; X-CodeMate-Request: 1; persistent throttling |
| GET /api/v1/auth/csrf | Refresh cookie + custom header; recover CSRF state after reload |
| POST /api/v1/auth/refresh | Refresh cookie + custom header + X-CSRF-Token |
| POST /api/v1/auth/logout | Refresh cookie + custom header + X-CSRF-Token |
| GET /api/v1/auth/me | Bearer access token, active user |
| GET /api/v1/users?offset=0&limit=20 | Bearer token, active ADMIN; maximum limit 100 |

All supplied Origin headers on session operations must match the explicit allowlist.
Non-browser clients may omit Origin but must supply the custom header. Passwords
require 12?128 characters and at least three character categories; usernames are
3?32 lowercase letters/digits/underscores, starting with a letter. Emails are
normalized to lowercase. Registration rejects extra fields and always creates USER.
There are no public role-promotion endpoints or default administrator credentials.

Explicit operator bootstrap, from backend (prompts twice; never logs the password):

```powershell
.\.venv\Scripts\python.exe scripts\bootstrap_admin.py --email 'operator@example.com' --username 'operator'
```

This creates a new account, rejects duplicates, and never promotes an existing user.

## Session and security controls

- Argon2id hashes with per-password random salts; verification rehashes if required.
- 15-minute HS256 JWTs require signature, issuer, audience, exp, iat, nbf, sub, jti,
  and an access token type. Roles and account activation are read from PostgreSQL.
- Refresh secrets use 384 bits of randomness. Only SHA-256 hashes are persisted.
  Old revocation and new session creation commit together under a row lock.
  Replay is denied; concurrent use produces one success and one unauthorized response.
- Seven-day refresh cookies are HttpOnly, host-only, SameSite=Strict, and scoped to
  /api/v1/auth. Production requires Secure cookies and HTTPS CORS origins. Local
  HTTP uses COOKIE_SECURE=false. Token responses use Cache-Control: no-store.
- CSRF tokens are HMAC-bound to the refresh cookie. A custom request header and
  exact Origin checking also prevent login CSRF and cross-origin form submissions.
- PostgreSQL-backed fixed-window login limits survive worker restarts: 10 attempts
  per account and 30 per peer IP per five minutes, including successful logins.
  Limits are persisted atomically; 429 responses carry Retry-After.
- Every response gets a server-generated request ID (except CORS middleware-handled
  preflights). Structured request logs exclude bodies, headers, query strings,
  email, passwords, and tokens. Unexpected errors return sanitized 500 responses.
- Missing/weak signing secrets, non-PostgreSQL URLs, unsafe algorithms, wildcard
  origins, and insecure production cookie settings fail configuration validation.

Frontend session handling: access tokens stay in a private in-memory session manager.
Refresh tokens stay in the backend's HttpOnly cookie; neither token is placed in
localStorage, sessionStorage, URLs, query caches, browser logs, or rendered account data.
The only persisted browser setting is `codemate-preferences` (theme/reduced motion).
Cookie-aware requests use `credentials: "include"` and `cache: "no-store"`.
After reload, `/auth/csrf` bootstraps the current cookie's CSRF value, then
`/auth/refresh` rotates it and `/auth/me` verifies the account. The CSRF value is
short-lived request state, re-bootstrapped inside the cookie mutation lock.
Native Web Locks serialize login/refresh/logout across tabs; BroadcastChannel sends
only signed-in/signed-out invalidations. Unsupported browsers fall back to an
in-tab queue; reliable multi-tab rotation requires Web Locks (tested in Edge).
Idle sessions renew five seconds before access expiry and recheck the profile;
protected GETs get at most one refresh and one retry on 401. Mutating requests
never retry automatically. Outages keep the workspace hidden with an explicit retry,
and failed server logout is clearly reported as local sign-out only.
Production frontend/API must be same-site HTTPS for Strict cookies.

Logout revokes the selected refresh session and clears its cookie. Already issued
stateless access tokens remain valid until expiry unless the account is deactivated.
Replay does not revoke every session for the user or a replacement session; session
family-wide compromise response is not implemented.

## Verification

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe -m pytest -q -W error
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m ruff format --check .
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m pip check
```

Tests refuse any target other than codemate_test_user on codemate_test_db at
127.0.0.1:5433. Fixtures apply real migrations and clear only dedicated test tables.
Migration downgrade/upgrade runs only in this test database. Do not run tests in
parallel against the same test database. The original three health tests remain.
Starlette 1.x uses httpx2 for its supported TestClient adapter; HTTPX remains
available for API clients. No warnings are suppressed.

Actual local outcome: **73 passed, 0 failed, 0 skipped, 0 blocked**, with warnings
as errors; Ruff, formatting, migration metadata checks, and dependency checks pass.
Frontend lint (zero errors/warnings), TypeScript, and production build pass.
**49 frontend unit tests and 5 real Edge E2E tests pass.** E2E uses only the guarded
test database and disposable accounts, including registration, login, reload,
profile/settings, logout, anonymous denial, admin access, mobile keyboard navigation,
cross-tab rotation/logout, outages, and unconfirmed revocation warnings.
Production-only npm audit reports zero findings; five high development-tooling
findings remain documented, with no supported braces patch at review time.

Detailed setup and manual API commands: [docs/WINDOWS.md](docs/WINDOWS.md).
Architecture: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
Actual results and known limits: [docs/PROGRESS.md](docs/PROGRESS.md).

## Frontend navigation and tests

| Route | Behavior |
| --- | --- |
| `/` | Public landing page with genuine service health |
| `/login`, `/register` | Validated forms; verified sessions redirect to dashboard |
| `/dashboard` | Protected overview, integration placeholders, live health and empty activity |
| `/dashboard/profile` | Safe account fields from `/auth/me` |
| `/dashboard/settings` | Browser-local appearance and current-session sign-out |
| `/dashboard/admin/users` | ADMIN-only read-only paginated directory; API enforces RBAC |

The protected layout starts in a restoring state, so server-generated HTML contains
no account data. This frontend gate does not replace backend JWT/role authorization.
The API cookie's auth-only path prevents using it for Next.js server-side auth;
no cookie scope or backend security rule was weakened.

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
npm.cmd run lint
npm.cmd run typecheck
npm.cmd run test
npm.cmd run build
npm.cmd run test:e2e
npm.cmd audit --omit=dev
npm.cmd audit
```

E2E needs installed Microsoft Edge, the backend venv, a healthy CodeMate database,
and free ports 3000/8001. It builds into `.next-e2e`, launches its own test API on
8001, and cleans up only its processes and exact disposable accounts. The normal
API on 8000 and normal `.next` build remain separate. Do not run backend pytest
concurrently against the shared dedicated test DB. Run the normal build after E2E
before standalone typecheck, because Next regenerates `next-env.d.ts` for its last
build directory. Detailed commands and limitations are in [WINDOWS](docs/WINDOWS.md).

## Structure

```text
backend/
  app/api/                 Routes and reusable auth/database dependencies
  app/core/                Settings, security, logging, safe errors
  app/db/                  SQLAlchemy base, engine, request sessions
  app/models/              Users, refresh sessions, GitHub connections/state, login limits
  app/schemas/             Input validation and safe response schemas
  app/integrations/github/ Bounded GitHub client, encryption, DTOs and log redaction
  app/repositories/        User and GitHub connection queries
  app/services/            Transaction boundaries and authentication logic
  alembic/                 Additive core and GitHub PostgreSQL migrations
  scripts/                 Local configuration and explicit admin bootstrap
  tests/                   PostgreSQL integration and regression tests
frontend/
  src/app/                 Public landing/auth pages and protected dashboard routes
  src/components/          Auth forms, workspace shell, dashboard and account UI
  src/lib/                 Typed Fetch API, Zod validation and memory-only sessions
  src/providers/           Auth, query cache, browser preferences and notifications
  src/tests/               Vitest / React Testing Library mocked-network tests
  e2e/                     Playwright real-backend browser scenarios
  scripts/                 Isolated test API, guarded DB preparation and cleanup
infrastructure/            Guarded database startup and initialization
Docker Compose at root     CodeMate-only PostgreSQL 16
```

Production-minded does not mean deployment-hardened: TLS/reverse proxy, backups,
registration abuse controls, secret rotation, retention jobs, and CI/deployment
infrastructure remain future work. Milestone 3 is COMPLETE; Milestone 4 is implemented
with live GitHub verification pending.


## GitHub workspace

After signing in, open `/dashboard/github`. Install the manually registered GitHub
App on selected repositories and authorize it through CodeMate. Credentials stay
encrypted on the backend. `/dashboard/repositories` provides authorized activity;
`/dashboard/cicd` provides workflow filtering and failed-job/log investigation.
Counts are scoped to the returned installation/page; monitoring uses explicit refresh.
Disconnect requires confirmation and reports remote revocation separately from local
credential deletion. Existing health, account and role-based pages remain available.

Run `backend/scripts/setup_github_key.py` to create an absent independent local key,
apply `alembic upgrade head`, and follow docs/GITHUB_INTEGRATION.md for the exact five
read-only App permissions and callback. No external application is registered for you.
Automated GitHub tests use a test-only controlled HTTP fixture, not personal GitHub
credentials. Current verification: 135 backend, 73 frontend and seven Edge E2E tests.
The five existing dev-tooling audit findings remain documented; production audit is zero.
