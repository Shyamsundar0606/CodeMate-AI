# GitHub integration - Milestone 4

Status: **IMPLEMENTED, LIVE VERIFICATION PENDING**. Automated tests use a controlled
GitHub HTTP transport. No live GitHub App client ID or client secret is configured;
no real authorization, installation, organization approval or live log download has
been verified. Production code calls GitHub's real endpoints when configured.
Milestone 5 has not started.

## Authentication choice and permissions

CodeMate uses a **GitHub App user authorization** flow, not an OAuth App, PAT,
installation-token bot or GitHub sign-in replacement. Existing CodeMate login remains
required. GitHub Apps provide fine-grained permissions and selected repository
installations; access is the intersection of the App installation and the GitHub
user's access. See [GitHub's user authorization documentation](https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/generating-a-user-access-token-for-a-github-app).

Register only these repository permissions:

| Permission | Level | Used for |
| --- | --- | --- |
| Metadata | Read-only (GitHub mandatory) | Authorized installation repository metadata |
| Contents | Read-only | Branch and commit metadata |
| Issues | Read-only | Issue listing |
| Pull requests | Read-only | Pull request listing |
| Actions | Read-only | Workflows, runs, jobs, steps and log downloads |

No account or organization permissions are needed. No write permissions, repository
source downloads, webhook receiver, workflow reruns or repository mutations are
implemented. Returned installations with permissions beyond read-only are rejected.
Endpoint requirements were checked against official [installations](https://docs.github.com/en/rest/apps/installations),
[branches](https://docs.github.com/en/rest/branches/branches), [commits](https://docs.github.com/en/rest/commits/commits),
[issues](https://docs.github.com/en/rest/issues/issues), [pull requests](https://docs.github.com/en/rest/pulls/pulls),
[workflows](https://docs.github.com/en/rest/actions/workflows), [runs](https://docs.github.com/en/rest/actions/workflow-runs)
and [jobs/logs](https://docs.github.com/en/rest/actions/workflow-jobs) documentation.

GitHub App permissions are configured at registration rather than broad OAuth App
`repo` scopes. The only requested scope is `offline_access`, currently supported by
GitHub Apps to request expiring user credentials and refresh capability; it does not
grant repository permissions. PKCE uses S256, an 86-character random verifier and a
43-character challenge. API requests use version `2026-03-10`.

## Exact manual App registration

1. Sign in to GitHub. Open **Settings > Developer settings > GitHub Apps > New GitHub App**
   (an organization owner can use the organization's Developer settings instead).
2. Choose a unique name, such as `CodeMate Local YourName`, and a description of
   read-only development monitoring. Homepage URL: `http://localhost:3000`.
3. Under **Identifying and authorizing users**, set the user authorization callback
   to **`http://localhost:8000/api/v1/github/callback`**. This is the backend callback,
   not the frontend route or test server on 8001. Leave expiring user access tokens
   enabled. Leave device flow disabled. Authorization after installation is optional;
   CodeMate's Connect action starts its own state-protected flow.
4. Leave the post-installation Setup URL blank. Disable **Active** under Webhook;
   this milestone uses explicit reads and has no webhook endpoint.
5. Set the five repository permissions above to Read-only. Leave all other
   repository/account/organization permissions at No access. Subscribe to no events.
6. For local use choose **Only on this account** under where the App can be installed.
   Create the App manually. No external App was registered by this implementation.
7. Note its **Client ID** (not numeric App ID). Generate a **client secret**. Store it
   only in the ignored backend environment file. Do not paste it into the frontend,
   terminal command arguments, a screenshot, a ticket or this documentation.
8. Install the App on your account, choose **Only select repositories**, and select
   a safe test repository. Organization repositories may need owner approval or an
   active SAML SSO session. Installing the App and authorizing a user are distinct.
9. Record the App's URL slug if you want CodeMate's installation link enabled.

For a deployed environment register exact HTTPS callback and frontend origins,
require secure cookies and use a managed secret store. GitHub Enterprise Server and
arbitrary API base URLs are deliberately unsupported. This flow needs neither a
GitHub App RSA private key nor an App ID because it uses user authorization.

## Environment and key setup

From PowerShell:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
.\.venv\Scripts\python.exe scripts\setup_github_key.py
notepad .env
```

The helper generates a valid independent Fernet key only when absent, preserves
existing values and never prints the key. If you copied the template and have a blank
`GITHUB_TOKEN_ENCRYPTION_KEY=` line, remove only that blank line before running the
helper; it deliberately refuses to overwrite existing configuration.
A valid local key was created in ignored
`backend/.env`. Complete these settings privately:

```dotenv
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/api/v1/github/callback
GITHUB_FRONTEND_ORIGIN=http://localhost:3000
GITHUB_APP_SLUG=
GITHUB_API_BASE_URL=https://api.github.com
```

`GITHUB_TOKEN_ENCRYPTION_KEY` is populated by the helper; do not insert an invalid
placeholder or reuse `JWT_SECRET_KEY`. Restart FastAPI after setting credentials.
Absent App credentials produce a clear **GitHub integration not configured** screen.
Partial or unsafe configuration is rejected. No `NEXT_PUBLIC_GITHUB_*` secret exists.
Use localhost consistently for frontend and callback during local authorization.

Fernet authenticates ciphertext containing user UUID, purpose and token. Copying a
credential to a different owner or using a refresh ciphertext as an access token is
rejected. Access tokens, refresh tokens and temporary PKCE verifiers are encrypted;
state/browser nonce values are stored as SHA-256 hashes. No credentials, including
encrypted ones, are returned by connection APIs.

**Rotation:** securely back up the current encryption key separately from database
backups. Changing it alone makes existing credentials unreadable. For this milestone,
disconnect each connection with the old key, change the key and reconnect; if the
old key is unavailable, remove connections through the safe disconnect API and
revoke the App authorization manually in GitHub. Do not decrypt tokens in terminal
output or perform an ad hoc SQL plaintext migration. A future operational migration
could use a key ring and audited ciphertext re-encryption. JWT and encryption key
rotation are separate operations. Client-secret rotation needs a backend restart.

## Connection lifecycle and isolation

```mermaid
sequenceDiagram
    participant UI as Authenticated Next.js UI
    participant API as FastAPI
    participant DB as PostgreSQL
    participant GH as GitHub App / REST API
    UI->>API: Bearer + cookie-bound CSRF: start connection
    API->>DB: Hashed state + browser nonce, encrypted PKCE verifier
    API-->>UI: Authorization URL + HttpOnly Lax callback cookie
    UI->>GH: User authorization with state + PKCE challenge
    GH->>API: Callback code + state; browser supplies callback cookie
    API->>DB: Validate single-use state, owner and initiating session
    API->>GH: Backend-only code exchange and account validation
    API->>DB: Save encrypted user credentials
    API-->>UI: Clean redirect with safe result code
    UI->>API: Authenticated repository or Actions read
    API->>GH: Fixed endpoint with backend token
    API-->>UI: Typed bounded metadata / redacted log text
```

The refresh cookie retains its existing `/api/v1/auth` path and SameSite Strict
behavior. Consequently connection mutations live under `/api/v1/auth/github`, where
that cookie is sent, rather than broadening its path or weakening CSRF checks.
They require bearer authentication, matching active refresh-session ownership,
allowed Origin, X-CodeMate-Request and a fresh X-CSRF-Token.

The separate state cookie is HttpOnly, host-only, SameSite Lax, callback-path-only,
10 minutes and Secure in production. Callback processing checks its browser nonce,
state expiry/single-use, active originating session and active user, with another
session check after GitHub network calls. A session rotated during authorization
requires a new connection attempt. Cancellation, upstream failure and ownership
conflict consume validated state. A clean 303 redirect exposes only an allowlisted
result code; callback codes/state and signed log queries are removed from application,
Uvicorn and HTTPX access logs. Configure any reverse proxy to omit/redact callback
query strings too; CodeMate cannot sanitize an external proxy's logs.

Unique constraints enforce one connection per CodeMate user and one CodeMate owner
per GitHub account. GitHub IDs are stable; usernames are display metadata. USER and
ADMIN each access only their own connection; being ADMIN grants no GitHub override.
Foreign keys cascade connection/state deletion when the CodeMate user is deleted.
Disconnect invalidates pending states, attempts GitHub's supported
[App authorization revocation](https://docs.github.com/en/rest/apps/oauth-applications),
always deletes local credentials, and reports `remote_revoked` honestly. Remote
revocation can affect all user tokens for this same App/account; it does not uninstall
the App or modify repositories. GitHub errors do not sign the user out of CodeMate.

Near expiry, refresh is serialized by a database connection row lock; rotated
credentials are committed even when a subsequent repository read fails. Expired
refresh credentials or GitHub 401 purge unusable credentials and require reconnect.
There is no credential mutation retry. Nullable token expirations/refresh values
support GitHub's non-expiring response shape, although expiring tokens are preferred.

## CodeMate API reference

All reads require CodeMate bearer authentication except the state-protected browser
callback. Owner/repo, installation IDs, page sizes and entity IDs are validated.

| Method | Route | Result |
| --- | --- | --- |
| GET | `/api/v1/github/connection` | Safe status/account metadata |
| POST | `/api/v1/auth/github/connect` | Start state + PKCE authorization |
| GET | `/api/v1/github/callback` | Validate browser callback; clean redirect |
| POST | `/api/v1/auth/github/disconnect` | Local deletion + remote revocation result |
| GET | `/api/v1/github/installations` | Authorized App installations |
| GET | `/api/v1/github/repositories` | One installation's authorized repository page |
| GET | `/api/v1/github/repositories/{owner}/{repo}` | Authorized metadata |
| GET | same repository prefix + `/branches` | Branches and commit references |
| GET | same repository prefix + `/commits` | Commit metadata; nullable author |
| GET | same repository prefix + `/pulls` | Pull request page; open/closed/all |
| GET | same repository prefix + `/issues` | Issue page excluding PR records |
| GET | same repository prefix + `/workflows` | Workflow page |
| GET | same repository prefix + `/actions/runs` | Run page; status/workflow filters |
| GET | same repository prefix + `/actions/runs/{run_id}` | Scoped run detail |
| GET | same repository prefix + `/actions/runs/{run_id}/jobs` | Jobs and step results |
| GET | same repository prefix + `/actions/jobs/{job_id}/logs` | Bounded log DTO |

Repository and nested routes require `installation_id`. Collections accept
`page=1..1000`, `per_page=1..100`; listing accepts `q` up to 100 characters and
`sort=name|updated|stars`. Search and sort operate **only on the fetched page**.
DTOs include `items`, `page`, `per_page`, `has_next`, nullable `total`, `scope` and
`fetched_at`. Next links must match the expected GitHub host/path; they are never
followed as arbitrary URLs. The next request is constructed from bounded parameters.

Repository access requires both a GitHub metadata read and membership in the
selected installation's authorized repository list. A public repository name alone
is insufficient. Membership lookup is limited to five 100-item pages; for larger
installations open the desired authorized page in the explorer before opening the
detail route. There is no fetch-all endpoint. Run/job requests stay inside the same
validated repository and returned run/repository IDs are checked.

## Frontend use and counts

Protected routes: `/dashboard/github`, `/dashboard/repositories`,
`/dashboard/repositories/[owner]/[repo]`, `/dashboard/cicd` and
`/dashboard/cicd/runs/[runId]`. Installation and repository/run context are held in
validated URL state; activity tabs preserve installation context. Select an
installation, explore its pages and open a repository. Activity includes Overview,
Branches, Commits, Pull Requests, Issues and CI/CD. The monitor supports repository,
workflow and status selection, explicit refresh, timestamps and completed-run
duration. There are no real-time push or automatic polling claims.

A completed run's conclusion determines success/failure, independently of HTTP
success. Investigation highlights failed jobs/steps and shows available log text;
it offers no invented explanation. AI-assisted diagnosis remains Milestone 5.
The overview previews the first accessible installation/repository: repository count
is installation-scoped; run, failure and PR counts describe their fetched pages.
Unavailable permissions or data remain unavailable, never fabricated totals.
Health, profile, preferences, ADMIN navigation and logout remain working.

## HTTP reliability, logs and retention

The synchronous HTTPX client matches the existing sync database/worker architecture.
It has fixed approved hosts, no proxy environment, eight request slots/connections,
3-second connect/pool and 5-second I/O timeouts, plus a 12-second stream processing
budget. One immediate retry is permitted only for safe GET 5xx reads without
Retry-After. There are no retries for 401/403/404/429, credential exchanges or
revocation. Primary and secondary rate limits expose safe retry/reset metadata and
block repeat reads during a bounded process-local backoff. UI queries do not retry
and suppress the retry button during rate limits; manual refresh still encounters
the backend backoff. These controls are per process, not distributed quotas.

JSON responses are limited to 2 MiB; compressed responses are rejected to avoid
unexpected decompression costs. Collections reject malformed/partial records rather
than silently inventing fields. Safe errors include not configured (503), not
connected (409), reauthorization/permission required (424), missing/not authorized
(404), validation (422), rate limited (429), unavailable (502) and timeout (504).
GitHub 401 becomes 424 so it cannot trigger CodeMate's session-expiry behavior.
Database exceptions return existing safe internal-error responses with request IDs.

GitHub's job log API supplies a temporary signed redirect. The second request has
**no Authorization or cookies**, follows no further redirects and accepts only HTTPS
port 443 hosts `pipelines.actions.githubusercontent.com` or
`productionresultssa[0-9]+.blob.core.windows.net`. These are a deliberately narrow
allowlist, not a guarantee that all GitHub log storage regions/hosts are covered.
An unsupported legitimate destination is rejected; open the job directly on GitHub.
Signed URLs and upstream authentication headers never reach the frontend.

Downloads are limited to 256 KiB / 4,000 rendered lines. Truncated incomplete lines
are dropped; invalid UTF-8 is replaced; ANSI/control/bidi characters are removed.
Known GitHub credentials, current client secret, AWS keys, JWTs, private keys and
common credential assignments are redacted. **Detection is imperfect**: review before
copying/sharing. The viewer renders React text inside a preformatted block, never
HTML, shows line numbers, filters within the bounded buffer and confirms copying up
to 200 visible lines. Missing, deleted and expired logs return safe unavailability.

No source code, repository bodies or raw logs are persisted. PostgreSQL stores only
connection metadata, encrypted credentials and one current authorization state per
user (replaced on a new connect; removed on disconnect/user deletion). Membership
cache holds repository IDs only, keyed by user, connection, token hash, installation
and repository; 15-second TTL, 1,024 entries. Backend rate backoff is capped at 512
hashed-credential entries. Frontend query keys contain CodeMate user ID and route,
with 15-second stale time and 60-second inactive garbage collection; log text remains
only in that user's bounded memory cache. Logout/session change/disconnect removes
GitHub queries. No localStorage/sessionStorage credential or GitHub cache persists.

Existing limitations remain: already issued CodeMate JWTs can stay usable until
expiry; native Web Locks are needed for robust cross-tab cookie serialization.
Single-use callback/credential network operations cannot be made transactionally
atomic with GitHub. A worker crash between successful upstream refresh and local
commit can require reconnect. No webhook detects revocation proactively; the next
GitHub request does. This is not a formal penetration test or full browser matrix.

## Automated and manual verification

Verified locally on 2026-10-11: 135 backend tests (original 73 + 62 GitHub tests),
73 frontend tests (original 49 + 24 new tests), seven Edge browser tests (original
five + two GitHub tests). PostgreSQL tests guard the dedicated test database/role on
5433. They verify new migrations from base, upgrade/downgrade, preservation of users
and sessions, schema consistency and isolation. The initial migration is unchanged.
Browser tests use test-only HTTPX MockTransport and an intercepted authorization
navigation; live App credentials are neither required nor used. Test transport
injection is rejected outside APP_ENV=test. No automated test establishes live OAuth.

Manual live checklist after registration/configuration:

1. Start services using docs/WINDOWS.md. Sign in to CodeMate and open GitHub connection.
2. Connect, inspect the GitHub consent screen's permissions and selected repositories,
   approve, and verify your actual login/avatar and last verified time.
3. Cancel another attempt; confirm an informative message and no credential exposure.
   Try a forged callback and an expired/replayed state; reconnect normally afterward.
4. Explore one selected public and one selected private repository. Compare metadata,
   branches, commits, issues and PRs to GitHub. Try an unselected repository and a
   different CodeMate user; private data must not appear.
5. Compare workflow runs/jobs/steps and a failed build to GitHub. Download available
   logs, check safe text/redaction/truncation and copy review. Verify a deleted log's
   unavailable state. Unknown signed log hosts should fail closed.
6. Disconnect with confirmation. Check local state is gone and remote revocation is
   explicitly confirmed or unconfirmed. Also revoke manually in GitHub settings and
   verify that the next CodeMate read asks for reconnection without logging out.
7. Verify organization/SSO access, pagination and natural rate-limit behavior without
   intentionally hammering GitHub. Check desktop/mobile navigation and logout.
8. Record actual live results and limitations in PROGRESS.md before declaring COMPLETE.

Dependency review retains Next.js / eslint-config-next 16.4.0. Full npm audit reports
the existing five high dev-tooling findings; production-only audit reports zero.
Registry braces remains 3.0.3 with no published patched version for
[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm).
No force fix, downgrade, finding suppression or speculative override was applied.
Python dependency compatibility (`pip check`) passes. No formal Python advisory audit
is claimed. HTTPX 0.28.1 is now a runtime requirement; cryptography 49.0.0 was added.

This milestone provides read-only structured inputs for future agents. It implements
no Ollama integration, AI analysis, voice input/output or autonomous changes.


## Main implementation files

- Backend composition/configuration: `app/main.py`, `app/core/config.py`,
  `app/core/logging.py`, `backend/.env.example`.
- Integration: `app/integrations/github/client.py`, `crypto.py`, `schemas.py`,
  `exceptions.py`, `rate_limit.py`, `authorization_cache.py`, `logs.py`.
- Persistence: `app/models/github_connection.py`,
  `app/repositories/github_connection_repository.py`,
  `alembic/versions/0002_github_integration.py`.
- Services/routes: `app/services/github_connection_service.py`,
  `github_repository_service.py`, `app/api/routes/github.py`.
- Setup/dependencies: `scripts/setup_github_key.py`, `requirements.txt`,
  `requirements-dev.lock.txt` (HTTPX promoted to runtime; cryptography 49 added).
- Frontend: `src/lib/github.ts`, `src/components/github/*`, five new protected
  route page files, existing API/session/auth provider, dashboard overview/shell
  and scoped CSS additions. No unrelated application behavior was changed.
- Verification: `backend/tests/test_github.py`, `tests/github_mock.py`,
  `frontend/src/tests/github.test.tsx`, added session cases, retained dashboard
  regression case, `e2e/workspace.spec.ts`, `scripts/e2e_backend.py`.
- Documentation: README, PROGRESS, ARCHITECTURE, WINDOWS and this guide.

The repository was already entirely untracked at the baseline; no commit or remote
PR was created, and no diff against a committed application baseline is claimed.
Ignored configuration, database volumes and existing user data were preserved.


## Milestone 5 consumption of read-only evidence

The local diagnostic worker reuses these exact authorized repository/run/job/log
services. No App permission, callback, encryption key or OAuth configuration change
is required. The AI cannot choose endpoints or request GitHub writes. Stored report
ownership is tied to the original CodeMate user and GitHub connection; access is
revalidated on creation, retry and execution. Disconnect deletes associated saved
investigations through a foreign-key cascade. Completed successful runs receive a
metadata summary and are never presented as CI failures.
See [AI_DIAGNOSTICS.md](AI_DIAGNOSTICS.md) and PROGRESS.md for separately labeled
live local fixture inference and live GitHub-backed failure-diagnosis status.
