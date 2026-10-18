# Progress

Current status: **Milestone 4 IMPLEMENTED, LIVE VERIFICATION PENDING**.
Milestones 1-3 remain complete. Historical results are retained below; the final
Milestone 4 entry is current. No Milestone 5 work has started.

## Milestone 1 â€” 2026-10-11

Status: foundation implemented; runtime verification blocked. Awaiting user
instruction before starting Milestone 2.

### Checklist

- [x] Inspect empty workspace and available commands.
- [x] Initialize Git in the existing root (no nested project directory).
- [x] Add Python 3.12 FastAPI application and typed `/health` endpoint.
- [x] Add Pydantic environment configuration and restricted development CORS.
- [x] Add three backend health/CORS tests and Ruff configuration.
- [x] Add Next.js / React / TypeScript / Tailwind starter page.
- [x] Add actual backend availability check, timeout, and retry state.
- [x] Add environment templates, ignore rules, and editor configuration.
- [x] Document Windows setup, architecture, limitations, and next steps.
- [ ] Install dependencies and generate frontend lockfile.
- [ ] Run backend tests and lint with Python 3.12.
- [ ] Run frontend lint, type check, production build, and runtime smoke check.

### Actual checks and outcomes

| Check | Outcome |
| --- | --- |
| Initial workspace listing | Empty |
| Repository instruction search | No AGENTS.md found in workspace |
| Python / Python launcher | Neither available on PATH |
| Node | v24.17.0 |
| npm | 11.13.0 via npm.cmd |
| npm.ps1 | Blocked by existing PowerShell execution policy |
| Git | 2.54.0.windows.1 |
| git init | Successful |
| Docker / Ollama | Neither available on PATH |
| Frontend dependency installation | Could not launch: execution helper setup refresh failed |
| Retry using root working directory | Same execution helper failure |
| Alternate Node runtime inspection | Runtime exited unexpectedly |
| Pytest / Ruff | Not executed: Python unavailable |
| Frontend lint / typecheck / build | Not executed: dependencies could not be installed |
| HTTP / browser smoke checks | Not executed: servers could not be launched |

No successful automated tests, builds, or server runs are claimed.
File creation was performed using the patch tool; subsequent runtime inspection
was blocked by tool failures. Dependency ranges are not yet locked or audited.

### Next steps

Install Python 3.12, reopen the terminal, and run the README verification commands.
Resolve any actual errors, record outputs here, and generate a frontend lockfile.
Docker, Ollama, and PostgreSQL are not prerequisites for the current health endpoint.
Milestone 2 requires explicit instruction: **Proceed to Milestone 2.**

## Frontend dependency security review â€” 2026-10-11

Scope: frontend dependency audit only; Milestone 2 has not started.
Reviewed frontend/package.json, package-lock.json, npm ls, and current npm registry
metadata. No application code, dependency declarations, or overrides were changed.
Ran npm install without force; npm reported the installation was up to date.

Installed dependency path (all five affected entries have dev: true in the lockfile):

```text
eslint-config-next@16.4.0
  @next/eslint-plugin-next@16.4.0
    fast-glob@3.3.1
      micromatch@4.0.8
        braces@3.0.3
```

Next.js remains 16.4.0. Production direct dependencies are Next.js 16.4.0,
React 19.3.0, and React DOM 19.3.0.

### Unresolved security finding and decision

Five high audit entries represent one root advisory propagated through the above
chain: GHSA-vfj7-8cjw-p6xm / CVE-2026-93687. Deeply nested brace patterns can exhaust
the Node.js call stack and cause denial of service. This affects development/lint
processes if attacker-controlled patterns reach the vulnerable parser. Merely being
a development dependency does not eliminate risk to developer machines or CI;
actual exploitability depends on pattern inputs. No exploit reachability proof is
claimed. No production dependency findings were reported by npm audit --omit=dev.
That audit result is not a guarantee that all runtime code is vulnerability-free.

Advisory: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm
Affected braces versions: <=3.0.3; patched versions: none at review time.
Registry latest braces is 3.0.3; micromatch is 4.0.8 and requires braces ^3.0.3.
Latest fast-glob is 3.3.3 and still requires micromatch ^4.0.8, so overriding it
would not fix this advisory. Stable eslint-config-next is 16.4.0 and its matching
plugin pins fast-glob 3.3.1. No supported compatible patched dependency was found.
Canary releases were not substituted for stable tooling.

npm suggests eslint-config-next@14.2.35 via audit fix --force. This incompatible
major downgrade was rejected. No audit suppression, forced fix, or speculative
override was applied. Keep lint glob configuration trusted, isolate CI jobs that
process untrusted changes, and revisit when upstream publishes a supported fix.
Deploy only production dependencies after building; omit=dev auditing does not
itself remove development packages from an existing installation.

### Actual verification results

| Command/check | Result |
| --- | --- |
| npm ls targeted packages | Passed; dependency chain confirmed |
| npm install | Passed; up to date; five high findings reported |
| npm run lint | Passed; zero errors/warnings |
| npm run typecheck | Passed after execution with write access to renamed root |
| npm run build | Passed; Next.js 16.4.0; / and /_not-found prerendered |
| Final npm audit | Exit 1; five high development-tooling findings remain |
| Final npm audit --omit=dev | Exit 0; zero vulnerabilities |
| npm ls --omit=dev | Passed; Next.js and React runtime dependencies confirmed |
| Production HTTP smoke check | Passed; HTTP 200 on localhost:3100; expected title, backend status, retry control, and AI unavailable content present |

The temporary production server was stopped after the smoke check. Browser
interaction, client-side retries, and live backend responses were not exercised;
application source was left untouched. Initial restricted registry requests failed
and typecheck could not write its incremental cache in the renamed project root.
Those checks were rerun successfully with approved access and a temporary npm cache.
An initial PowerShell lockfile parsing attempt failed; Node JSON parsing subsequently
confirmed versions and dev flags. No successful checks are inferred from failures.

Remaining: recheck the advisory and stable upstream releases for a supported patch.
The five high findings remain documented; no safe dependency fix is available today.


## Milestone 2 ? 2026-10-11

Status: **COMPLETE for the defined local milestone**. Milestone 3 has not started.
This entry supersedes the initial Milestone 1 runtime-blocked status; the existing
foundation was preserved and reverified. It does not claim production deployment
or completion of later hardening/infrastructure milestones.

### Implementation and environment

- Existing root D:\shyam\Projects\CodeMate-AI inspected, including README,
  architecture/progress, backend/frontend configuration, Git status, and env key
  names. No AGENTS.md or existing Compose file was found. Initial Git files were
  untracked; no commits were created or unrelated user changes discarded.
- Host access verified Python 3.12.10, Docker Engine 29.6.2, Compose 5.3.1.
  Restricted execution initially did not expose host Python/Docker correctly;
  those tool failures were resolved using approved host access.
- Confirmed VoxHire healthy on 5432 and port 5433 free before initial binding.
  CodeMate owns codemate-postgres, project codemate-ai, network codemate-ai_default,
  and volume codemate-ai-postgres-data. It binds only 127.0.0.1:5433 -> 5432.
- Development codemate_db/codemate_user and test codemate_test_db/codemate_test_user
  have different local credentials and connection permissions. Test role access
  to development is explicitly denied and tested. The API role is non-superuser
  and lacks database/role creation privileges. Separate codemate_owner bootstrap
  credentials are never used by the API. No additional test host port is published.
- Added typed SQLAlchemy models, pooled psycopg sessions, transactional services,
  repositories, Alembic revision 0001_backend_core, Argon2id, verified HS256 JWTs,
  persistent opaque refresh sessions, locked rotation, logout, DB-backed RBAC,
  paginated admin listing, explicit new-admin CLI, validated config, narrow CORS,
  CSRF bootstrap/protection, request IDs, and sanitized errors/logging.
- Preserved existing env values; generated only missing random credentials/keys
  in ignored root .env, backend/.env and backend/.env.test. Example files are safe.
  Added a tested Windows/Python 3.12 development dependency lock.
- No frontend component or authentication UI changes; no Milestone 3 work, AI,
  GitHub integration, voice, Redis, Celery, LangGraph, or automation was added.

### Verification history and issues fixed

The first test run passed 65 tests with one Starlette TestClient deprecation.
Installed its officially supported httpx2 adapter while retaining HTTPX; no warning
filters were added. A strict follow-up run caught a pooled connection cleanup
warning (68 passed, 1 failed). Fixed guaranteed lifespan disposal and separate
application lifecycles for concurrent clients; strict tests subsequently passed.
Initial code syntax/import-order/format errors were corrected before passing checks.

The final privilege audit found PostgreSQL rejects stripping SUPERUSER from its
bootstrap account. Separated/renamed that owner role and created the ordinary app
role, preserved development data and its existing app password, transferred only
CodeMate development objects, and removed the temporary maintenance role. Updated
fresh initialization accordingly. The health check now executes an authenticated
TCP SELECT 1 instead of pg_isready, preventing premature readiness during init.

Verified corrected initialization using one fresh temporary CodeMate PostgreSQL
container with no network/host ports and tmpfs storage. It created both ordinary
roles/databases successfully. Removed only that newly created temporary container
and its temporary secret file. The dedicated persistent CodeMate volume was never
removed; no VoxHire containers/networks/volumes were modified.

### Final automated and regression results

| Check | Actual outcome |
| --- | --- |
| Backend pytest -q -W error | 73 passed; 0 failed, skipped, blocked; no warnings |
| Original Milestone 1 health/CORS tests | All 3 pass, included in 73 |
| Registration/login/JWT tests | Pass; normalization, duplicates, invalid credentials, inactive users, expiry/type/signature/issuer/audience/algorithm validation |
| Refresh/session tests | Pass; rotation, expiry, revocation, replay, concurrent reuse, logout, rollback, CSRF/reload bootstrap |
| RBAC tests | Pass; anonymous 401, USER 403, ADMIN pagination, current DB roles/status, safe responses |
| PostgreSQL tests | Pass; persistence, constraints, rollback, session cascades, real migrations, test-only downgrade/upgrade, drift checks, test-role isolation |
| Security settings/cookies/logging | Pass; missing/unsafe config fails, Secure production cookies, no raw credentials in logs, sanitized validation/errors, request IDs |
| Ruff lint / format | Pass; 40 files formatted consistently |
| Alembic development upgrade/current/check | Pass; 0001_backend_core (head); no drift |
| Development/test database identity and privilege checks | Correct DB/role, internal port 5432, both app/test roles non-superuser; matching head |
| Fresh initialization check | Pass; corrected app/test role separation with no published ports |
| pip check | No broken requirements |
| Frontend lint / typecheck / production build | All pass; Next.js stays 16.4.0 |
| Real headless Edge browser | API online, retry, CORS /health/ready 200, anonymous /auth/me 401; no uncaught browser errors |
| npm audit --omit=dev | Exit 0; zero findings |
| npm audit | Exit 1; same five high development-tooling findings remain |
| Generated-secret scan / Git ignore checks | Pass; local secret files ignored; generated values absent from source/docs |
| Final Docker status | CodeMate healthy on 5433; VoxHire remains healthy on 5432 |

Temporary frontend/API verification processes were stopped. CodeMate PostgreSQL
remains running with persistent storage. Normal operator startup/stop affects only
codemate-ai. No default administrator was created.

### Security findings and remaining limits

The documented braces GHSA-vfj7-8cjw-p6xm chain remains a development-tooling issue.
No compatible supported fix exists at review time; no force downgrade, suppression,
or speculative override was applied. The production-only npm audit stays clean.

Production deployment still requires TLS/proxy policy, backups, secret/JWT rotation,
registration abuse controls, dependency supply-chain review, and session/throttle
retention jobs. The local Compose bootstrap password is visible to trusted Docker
operators. Limits use direct peer IP; proxy trust must be deliberately configured.
Fixed-window account limits can temporarily lock out legitimate users under attack.
No password reset, email verification, MFA, or session-family compromise revocation
is provided. Logout revokes the selected refresh session; stateless access JWTs
otherwise remain valid until expiration. The development lock targets the tested
Windows environment; production/platform-specific locking remains future work.

Full commands and expected behavior: docs/WINDOWS.md. Architecture: docs/ARCHITECTURE.md.
Stop after this milestone's report. Do not begin Milestone 3 without user instruction.

## Milestone 3 — Frontend authentication and developer dashboard — 2026-10-11

Status: **COMPLETE**. Implemented only Milestone 3 in the existing Next.js project.
Before editing, inspected the complete frontend, all four project documents,
FastAPI routes/schemas, cookie/CSRF/CORS code, existing tests, dependencies and Git
status. The repository remains uncommitted/untracked as at task start; no commit,
branch, or publication was created. No unrelated application code was changed.
Backend application/security code, migrations and credentials were preserved.

### Implemented behavior

- Public landing page, registration and login with React Hook Form/Zod validation,
  password confirmation/visibility, proper duplicate/credentials/rate-limit errors,
  accessible labels and disabled submission until the actual API call finishes.
  Registration sends only username/email/password and always uses backend USER assignment.
- Guarded dashboard, profile, browser-local settings and optional complete read-only
  ADMIN directory with pagination. Identity and role come from authenticated
  `/auth/me`; backend RBAC remains authoritative, including direct URL/403 handling.
- Responsive navy/charcoal/cyan/violet interface with light theme, desktop sidebar
  collapse, native mobile modal navigation, skip link/focus styles, account menu,
  safe loading/error states, error boundaries and notifications.
- Honest repository/CI/build/AI placeholders and recent-activity empty state. Shared
  real `/health` and `/health/ready` queries show current availability, last success,
  bounded manual retry and 60-second polling independently of user authentication.
- Typed Fetch client and runtime schemas, eight-second timeout, credentials/no-store,
  generic sanitized errors, one bounded refresh/retry for authenticated GETs only.
- Memory-only access tokens; refresh cookies stay HttpOnly. Reload restoration uses
  CSRF bootstrap, rotation and profile verification. Native Web Locks coordinate
  login/refresh/logout across tabs; CSRF bootstrap stays inside that lock.
  Single-flight promises coalesce in-tab renewal; broadcasts contain invalidations only.
- Idle revalidation near expiry and on return to an overdue tab. Terminal 401 clears
  identity; outages hide protected content and offer retry. Stale generations cannot
  resurrect auth or return protected data after session change. User caches clear on sign-out.
- Logout clears local state immediately and calls the correct CSRF-protected endpoint.
  A successful 204 is labelled server revocation. Failure clearly warns of local-only
  sign-out and possible cookie restoration after reload. Stateless JWT lifetime is unchanged.
- LocalStorage holds only theme/reduced-motion preferences; no credentials, tokens,
  signing secrets, role overrides or backend-persistence claims were introduced.

### Routes

| Route | Access / content |
| --- | --- |
| `/` | Public landing + live service health |
| `/login` | Login; verified guests redirect to dashboard |
| `/register` | Public USER registration; success navigates to login |
| `/dashboard` | Verified account overview, real health, future-feature empty states |
| `/dashboard/profile` | Safe API profile fields |
| `/dashboard/settings` | Browser preferences and active-session logout |
| `/dashboard/admin/users` | ADMIN-only read-only paginated list; backend enforces RBAC |

The protected layout renders restoration/loading on the server, with no account
content. The backend's auth-only cookie path is unchanged; there is no pretend
Next.js server-side session check or client boolean that bypasses backend security.

### Files created and modified

Modified existing files:

```text
.gitignore
README.md
docs/PROGRESS.md
docs/ARCHITECTURE.md
docs/WINDOWS.md
frontend/package.json
frontend/package-lock.json
frontend/next.config.ts
frontend/eslint.config.mjs
frontend/tsconfig.json (Next-generated E2E type includes; strict stays enabled)
frontend/src/app/layout.tsx
frontend/src/app/page.tsx
frontend/src/app/globals.css
frontend/src/components/backend-status.tsx (compatibility re-export)
```

New frontend files (all paths below are relative to frontend):

```text
vitest.config.mts
playwright.config.ts
e2e/workspace.spec.ts
scripts/run-e2e.mjs
scripts/e2e_backend.py
src/app/error.tsx
src/app/not-found.tsx
src/app/(auth)/login/page.tsx
src/app/(auth)/register/page.tsx
src/app/(protected)/dashboard/layout.tsx
src/app/(protected)/dashboard/page.tsx
src/app/(protected)/dashboard/error.tsx
src/app/(protected)/dashboard/profile/page.tsx
src/app/(protected)/dashboard/settings/page.tsx
src/app/(protected)/dashboard/admin/users/page.tsx
src/components/auth/auth-frame.tsx
src/components/auth/auth-guard.tsx
src/components/auth/guest-gate.tsx
src/components/auth/form-fields.tsx
src/components/auth/login-form.tsx
src/components/auth/register-form.tsx
src/components/dashboard/dashboard-shell.tsx
src/components/dashboard/overview.tsx
src/components/dashboard/system-status.tsx
src/components/dashboard/profile.tsx
src/components/dashboard/settings.tsx
src/components/dashboard/admin-users.tsx
src/components/ui/brand.tsx
src/components/ui/page-state.tsx
src/hooks/use-system-status.ts
src/lib/api/client.ts
src/lib/api/auth.ts
src/lib/auth/session.ts
src/lib/auth/lock.ts
src/lib/auth/validation.ts
src/providers/app-providers.tsx
src/providers/auth-provider.tsx
src/providers/preferences-provider.tsx
src/providers/toast-provider.tsx
src/types/api.ts
src/tests/setup.ts
src/tests/fixtures.ts
src/tests/api.test.ts
src/tests/session.test.ts
src/tests/provider.test.tsx
src/tests/forms.test.tsx
src/tests/dashboard.test.tsx
```

Generated Next references/build outputs, browser screenshots/results and test lock
are ignored. No backend dependency or application source file changed.

### Actual verification results

| Check | Actual result |
| --- | --- |
| npm install | Up to date; package/lock consistency verified; 5 existing high findings |
| npm run lint | Exit 0; zero errors, zero warnings |
| npm run typecheck | Exit 0; TypeScript strict preserved |
| npm run test | 49 passed in 5 files; 0 failed/skipped |
| npm run build | Exit 0; Next.js 16.4.0; all 8 application/not-found routes generated |
| npm run test:e2e | 5 passed in real headless Microsoft Edge; 0 failed/skipped |
| Backend pytest -q -W error | 73 passed; 0 failed/skipped; no warnings |
| npm audit | Exit 1; exactly 5 high, 0 other findings; same development-only chain |
| npm audit --omit=dev | Exit 0; zero vulnerabilities |
| npm ls | Next/ESLint config/plugin 16.4.0; React 19.3.0; no incompatible downgrade |
| npm view braces version | 3.0.3; no published patched version |
| Test-helper Ruff lint/format | Pass |
| Generated backend/database secret scan | Pass; no generated values in frontend source/docs |
| Final E2E cleanup | 0 disposable E2E users left; test ports and lock removed |
| Final service check | Existing API still on 8000; CodeMate healthy on 5433; VoxHire healthy on 5432 |
| Screenshot review | Desktop dark overview/admin/registration, mobile overview, light settings reviewed |

Unit tests exercise validation and confirmed form submissions, duplicate/rate/invalid
credentials, cookie/CSRF headers, memory-only tokens, restoration/single-flight
renewal, expiry and bounded retries, idle renewal/outage stopping, logout/revocation
failure, stale responses, cross-tab invalidations/lock ordering, protected/guest
navigation, role-based UI and 403, admin pagination, profile allowlists, health
loading/online/outage/last-success states, honest empty states and local preferences.

The five final E2E tests actually ran against the unmodified FastAPI app, real
PostgreSQL and production-built frontend in Edge. They cover:

1. UI registration/login, profile, real cookie rotation on reload, preferences,
   server logout/cookie removal and anonymous rejection of protected routes.
2. Real duplicate registration and invalid-credential responses.
3. Mobile layout with no horizontal overflow, keyboard focus within native dialog,
   Escape/navigation, concurrent reloads and cross-tab logout invalidation.
4. Test-only backend ADMIN assignment and read-only real user directory.
5. Aborted-network outage hiding/recovery and persistent local-only logout warning.

Initial browser runs failed on ambiguous test selectors (password visibility control,
Next route announcer and hidden account-menu email). Corrected selectors to exact
field names and scoped assertions to main content; the final complete suite passes.
The normal successful flow reported zero uncaught browser errors.

### Test isolation and security findings

E2E uses only codemate_test_db / codemate_test_user at 127.0.0.1:5433. The helper
validates both configuration and live DB identity, ignores caller DB overrides,
applies real migrations, and clears only dedicated test throttle rows. Disposable
accounts use random per-run names/passwords; exact names/emails are cleaned afterward
with cascading refresh deletion. Admin promotion exists only in this guarded test
helper, never in application routes or UI. No permanent demo account or production
credentials were created. Backend pytest and E2E were run sequentially.

The runner uses an owned test API on 8001 and frontend on 3000, refuses occupied
ports, and stops only its child processes. The existing development API on 8000
and CodeMate/VoxHire containers were left untouched. `.next-e2e` is isolated from
the normal `.next` build; normal production build restores Next's generated type
references after browser verification. Traces/video are off; artifacts are ignored.

The five high findings remain:

```text
eslint-config-next@16.4.0 [dev]
  @next/eslint-plugin-next@16.4.0
    fast-glob@3.3.1
      micromatch@4.0.8
        braces@3.0.3
```

[GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm)
reports stack-exhaustion denial of service for deeply nested glob patterns through
braces 3.0.3, with no patched version. Registry and audit checks confirmed no
compatible supported fix. Audit proposes incompatible eslint-config-next 14.2.35;
it was not installed. There is no force fix, downgrade, suppression or speculative
override. This chain is development glob/lint tooling; attacker-controlled patterns
could disrupt tooling. Production-only npm audit remains zero. No additional
vulnerability finding was introduced by the new libraries.

### Known limits and stop point

Reliable multi-tab cookie rotation needs native Web Locks; unsupported browsers
have only in-tab serialization, and BroadcastChannel absence delays other-tab UI
invalidation. Tested Edge supports both. Browser coverage is desktop/mobile Edge,
not a complete device/browser matrix or formal WCAG certification. API failures do
not prove a user is signed out; local-only logout cannot clear an HttpOnly cookie
without a working API. Existing JWT/session-family and production operational
limitations documented in Milestone 2 still apply. No unsupported profile/password
editing, account settings persistence or imaginary security features were added.

Milestone 3 is COMPLETE. All required functional, backend regression, frontend and
selected browser checks pass. GitHub integration, AI, Ollama, voice and automation
remain future milestones. **Milestone 4 has not started. Stop after this report.**


## Milestone 4 - 2026-10-11

Status: **IMPLEMENTED, LIVE VERIFICATION PENDING**.

Implemented GitHub App user authorization (state, browser nonce, PKCE S256), encrypted
backend access/refresh credentials, owner-bound ciphertext, session/CSRF-protected
connect/disconnect, credential renewal/revocation, safe metadata and per-user isolation.
The existing refresh cookie path and security settings remain intact. One GitHub
account can belong to only one CodeMate account. No PAT input or GitHub write API exists.

Additive migration `0002_github_integration` creates connection/OAuth-state tables;
`0001_backend_core` is unchanged. Development upgrade preserved existing users and
refresh sessions. Dedicated PostgreSQL tests verify base-to-head, additive upgrade,
downgrade, constraints, ownership/cascades and schema consistency. Development head
is 0002; Alembic check reports no drift. CodeMate remains on 5433. No VoxHire resource,
port 5432, volume or network was modified, stopped or removed by CodeMate commands.

Implemented authenticated installations, authorized repository pages/details,
branches, commits, PRs, issues excluding PR records, workflows, runs, jobs, steps and
bounded log reads. Fixed GitHub endpoints, strict pagination/response bounds,
process-local rate backoff, safe timeouts/errors and owner/token-separated membership
cache protect reads. Signed log downloads use approved HTTPS hosts without bearer
headers or cookies. Logs are redacted, bounded and rendered as text; redaction is
explicitly imperfect. No source code or raw log persistence was added.

Protected connection, explorer, repository activity, CI/CD monitor and run
investigation pages are integrated with sidebar and overview. Counts clearly identify
their page/installation scope; no partial page is presented as an account-wide total.
Manual refresh, error/empty states, confirmed disconnect and safe log search/copy are
implemented. Health, profile, preferences, ADMIN access and logout regressions pass.

### Actual verification

- Backend: **135 passed**, warnings treated as errors; original 73 + 62 GitHub tests.
- Frontend: **73 passed**; original 49 cases retained + 24 new GitHub/session cases.
  The old disconnected-overview assertion now reflects the implemented GitHub link
  and the unchanged Milestone 5 placeholder.
- Browser: **7 passed, 0 failed, 0 skipped**, headless Edge; all original five plus
  anonymous GitHub-page protection and the controlled connection/explorer/Actions/
  logs/errors/disconnect/mobile flow. Desktop/mobile screenshots were reviewed.
- Ruff and formatting pass. Frontend lint has zero errors/warnings; strict TypeScript
  and normal Next.js 16.4.0 production build pass. Python `pip check` passes.
- Initial development migration upgrade preserved user/session counts; test migration
  roundtrips and schema checks pass; Alembic development head is 0002 with no drift.
- Full npm audit: **5 high findings**, exit 1. Production-only: **0**, exit 0.
  Same dev-only chain: eslint-config-next 16.4.0 -> @next/eslint-plugin-next 16.4.0 ->
  fast-glob 3.3.1 -> micromatch 4.0.8 -> braces 3.0.3. Registry latest braces remains
  3.0.3, latest compatible eslint-config-next remains 16.4.0. There is no supported
  patched version for GHSA-vfj7-8cjw-p6xm. No force, downgrade, suppression or override.

A callback-log test initially exposed the separate `httpx2` access logger; both HTTPX
variants now redact callback/signed URL queries. Refresh credentials now remain
committed if the following upstream read fails. The first new browser test run had
an ambiguous alert selector (Next.js route announcer); the corrected complete suite
passes. These resolved failures are not outstanding findings.

### Live status and limits

**IMPLEMENTED. AUTOMATED TESTS PASSED. LIVE GITHUB CONNECTION NOT VERIFIED.**
A valid independent local encryption key was generated only in ignored backend/.env.
GitHub App client ID/secret and installation still require manual setup; no external
App was registered and no successful live OAuth/API/log test is claimed. Test HTTPX
transport is restricted to APP_ENV=test and uses only disposable credentials.
See [GITHUB_INTEGRATION.md](GITHUB_INTEGRATION.md) for exact registration, permissions,
callback, environment, API reference, key rotation, live checklist and limits.

Known limits: current-page repository search/sort; bounded 500-repository direct
membership lookup (open an explorer page for larger installations); narrow signed
log host allowlist may reject a legitimate new GitHub host; imperfect secret redaction;
15-second membership freshness; process-local caches/backoff; no webhook/push updates;
Edge desktop/mobile coverage, not a full browser matrix or formal penetration test.
A refresh crash after GitHub rotates but before DB commit may require reconnect.
Existing JWT expiry and browser cross-tab limitations still apply. No Python security
advisory audit is claimed beyond dependency compatibility checks.

Milestone 4 remains **IMPLEMENTED, LIVE VERIFICATION PENDING** until the documented
manual authorization checklist passes. Milestone 5, AI diagnoses, Ollama, voice and
GitHub repository/workflow mutations have not started. Stop after this verification.


Final verification note: an interrupted tool session coincided with an unavailable
Docker daemon. The existing Docker Desktop installation was started; both existing
CodeMate and VoxHire containers were confirmed healthy. No project container was
stopped/deleted, and only CodeMate test persistence checks were rerun (135 pass).
The final formatted lint check found two unescaped JSX apostrophes; they were fixed,
then lint and strict TypeScript passed. Browser avatar requests now use controlled
test fixtures too; they are not live GitHub account verification.

Final captured reruns: backend **135 passed in 59.11s**, frontend **73 passed**,
Edge **7 passed in 16.0s**, no skips. The ordinary build and strict TypeScript pass
after E2E, with generated types restored to `.next`. `npm install` was up to date;
final production audit remains zero and full audit remains five high findings
(exit 1, intentionally unresolved). Test-only API8001 and Next3000 children and
disposable browser accounts were cleaned up by the guarded runner.


### Milestone 4 follow-up: job log viewer (2026-10-11)

Inspected the committed CI/CD investigation button, frontend/backend Job schemas,
repository authorization service and bounded GitHub log client. In this checkout,
the View logs button already has no disabled condition; neither Job schema contains
or requires logs_url. The reported disabled state was not reproduced, so no claim
is made that its cause was identified. A stale running frontend is a possibility,
not an established diagnosis; restart/rebuild and reload the investigation page
if its rendered button differs from this source.

The scoped viewer improvement makes View logs an explicit non-submit button with
expanded/control accessibility state and focuses the selected viewer, so the click
is apparent even when logs render below the job list. Added explicit log loading,
empty/unavailable text, and manual retry after an error or empty response. Existing
rate-limit retry restrictions remain in effect. Successful and failed jobs remain
clickable without inspecting a log URL or guessing upstream availability.

No backend production code, authorization, App permissions or schemas changed.
The backend verifies installation/repository membership and job metadata, then
requests GET /repos/{owner}/{repo}/actions/jobs/{job_id}/logs with the user's App
credential. It validates the signed redirect and downloads without credentials.
The existing HTTPS host allowlist, one-hop redirect handling, timeouts, 256 KiB /
4,000-line limits, redaction, no-store responses and user isolation remain intact.
API reference: https://docs.github.com/en/rest/actions/workflow-jobs#download-job-logs-for-a-workflow-run

Actual verification results:
- Backend: 139 passed in 47.90s with python -m pytest -W error; no skips/failures.
  Ruff lint and formatting checks passed (58 files formatted).
- Frontend: 79 passed in 5.36s. ESLint with --max-warnings=0, TypeScript and the
  Next.js 16.4.0 production build passed.
- Added four backend cases covering completed success/failure without logs_url,
  unavailable HTTP 404/410 responses and successful retry. Added six frontend cases
  covering button enablement, request-on-click, viewer focus, loading, safe 404/502
  errors with retry, and empty-log recovery. Existing redirect/redaction/limits and
  frontend HTML-escaping tests remain enabled and pass.
- Live App-authorized service verification used the existing stored connection:
  Shyamsundar0606/CodeMate-AI run 38149017752 was completed/success; job 114498333499
  returned 63,039 characters of redacted log text, not truncated. Only counts/status
  were printed; no tokens, secrets, signed URLs or log content were output or saved.
  This verifies the actual backend service path, not a new browser OAuth flow or a
  reproduction of the reported live disabled button. Browser E2E was not rerun.
- Existing five high development-tool dependency findings were not changed or
  re-audited in this scoped fix. No dependency upgrades, commits or pushes performed.

Changed files: frontend/src/components/github/investigation.tsx,
frontend/src/tests/github.test.tsx, backend/tests/test_github.py, docs/PROGRESS.md.
Milestone 5 has not started.


## Milestone 5 - Local AI-powered CI failure diagnosis (2026-10-12)

**IMPLEMENTED, LIVE VERIFICATION PENDING.** All implemented automated and local
fixture checks pass. **LIVE OLLAMA FIXTURE DIAGNOSIS VERIFIED.**
**LIVE GITHUB FAILURE DIAGNOSIS NOT YET VERIFIED:** the existing App-authorized
repository returned zero failed workflow runs and no additional failure page.
No deliberately failing workflow, disposable branch or GitHub write was created.
Historical CodeMate run 38149017752 still reports completed/success.

### Implemented scope

- Native local Ollama JSON-schema client, installed-model discovery/status,
  exact loopback-only endpoint, remote/cloud-model rejection, response/context/
  output/time limits and independent Pydantic validation. Optional for API startup.
- Eight finite LangGraph nodes: authorize, fetch_run, fetch_jobs, collect_evidence,
  extract_signals, local_diagnosis, ground_findings, build_report. Worker commits
  the typed report atomically. No cycles, model-selected tools, shell execution,
  code application, workflow changes, paid inference or external model fallback.
- Deterministic failure extraction with context, deduplication, stable IDs,
  redaction, per-job/total budgets and honest partial/missing evidence. Findings
  require existing evidence IDs and exact quotes. Unsupported recognizable details
  are flagged LOW; suspicious credential-disclosure output is rejected.
- Durable owner-scoped PostgreSQL queue/history with UUIDs, UTC timestamps,
  constraints, indexes and bounded JSONB reports. User/connection deletion cascades.
  Default 30-day terminal-report retention while the worker runs; explicit delete.
- Per-user admission row locking; account/job/global worker advisory locks;
  interrupted job-level recovery; at most three execution attempts; manual retry,
  cooperative cancellation and fresh row-lock checks before report completion.
- Authenticated AI status/models/history/report and create/retry/cancel/delete.
  Mutations preserve matching cookie session, CSRF, Origin and custom-header checks.
  Browser auth-path aliases preserve the original HttpOnly cookie path.
- `/dashboard/ai` overview/history and `/dashboard/ai/investigations/[id]` report;
  CI/CD Analyze with AI action, successful-run No failure detected behavior,
  durable bounded polling, keyboard evidence panels, retry/cancel/delete and copy
  warning. No frontend-to-Ollama requests or fabricated dashboard counts.

### Actual verification

| Check | Result |
| --- | --- |
| Windows Python 3.12, full Pytest -W error | **191 passed**, 0 failed/skipped; 123.30s |
| Clean Linux Python 3.12, actual backend CI commands | **191 passed**, 0 failed/skipped; 63.29s |
| Frontend unit tests | **98 passed**, 0 failed/skipped; final 7.32s |
| Real Edge E2E, all seven existing flows extended | **7 passed**, 0 failed/skipped; final 19.0s |
| Ruff lint / formatting | Pass; backend 74 files, helper included 75 |
| ESLint --max-warnings=0 | Pass |
| Strict TypeScript | Pass, including after normal build following E2E |
| Next.js 16.4.0 production build | Pass; new AI routes present |
| Python pip check | No broken requirements |
| Alembic development upgrade/check | Head 0003_ai_investigations; no schema drift |
| Existing development users/sessions/GitHub connections | Counts preserved by additive upgrade |
| Test migration/schema checks | Fresh/base-head roundtrip, 0003-0002-head preservation and constraints pass |
| Local-secret scan of changed/new files | No exact local credential matches; values never printed |
| npm audit --omit=dev | 0 findings, exit 0 |
| Full npm audit | Existing 5 high dev-tooling findings, exit 1 |

The original 139 backend and 79 frontend tests remain enabled; 52 backend and
19 frontend cases were added. Fixtures cover Pytest assertions, missing dependency,
TypeScript compilation, npm dependency install, PostgreSQL connection, migration,
permissions, timeout, resource exhaustion, prompt injection and successful runs.
Coverage includes provider offline/missing/timeout/malformed/truncated/oversized
output, graph transitions, partial/missing/multiple-job evidence, valid/invalid
references, persisted errors, idempotency/concurrent creation, owner/CSRF boundaries,
worker locks, interruption, finite retry, in-flight cancellation/deletion, retention
and additive migration preservation. Existing auth/session/GitHub security tests pass.

Edge additionally verifies AI progress/completion, evidence Enter-key expansion,
history/reload, protected AI routes, unavailable model messaging, and desktop/mobile
report/history layout with no horizontal overflow. Screenshots were visually
reviewed. Browser requests use controlled GitHub/Ollama responses through the real
FastAPI services and isolated PostgreSQL. This is not live inference evidence.

### Real local inference

Ollama was already installed/reachable at 127.0.0.1:11434, reporting version 0.40.3.
Installed `qwen2.5-coder:3b` was selected: 3.1B/Q4_K_M, 1,929,912,626 disk bytes.
Machine: approximately 16 GB RAM, 16 logical processors, RTX 3050 Laptop GPU with
approximately 4 GB VRAM. No model was pulled/downloaded by this implementation.
Other installed models were inspected but not selected for this laptop workload.

`python scripts/verify_local_ai.py` used a harmless Pytest assertion fixture,
controlled GitHub transport and **real local Ollama**. LangGraph completed;
Pydantic schema and exact evidence references validated; one finding/two evidence
records persisted and reloaded through the authenticated report path. The exact
random disposable test account and its cascaded report were then removed.
Initial measurement: 11.41s; final verification: **8.77s**. Ollama ps reported
2.3 GB loaded size, **100% GPU**, 8,192 context, llamacpp runner. These are observed
local fixture timings, not a general benchmark. Evidence completeness was complete;
no context truncation occurred for this small live fixture. Truncation/deadline/
provider error behavior is separately covered by deterministic automated tests.

Only the native loopback provider is configured/invoked; no paid/hosted LLM API,
model write tool or trace export was used. Prompts, raw model output, credentials,
signed URLs and full logs were not printed or saved. No packet-level audit is
claimed. Local inference does not eliminate hallucination or secret-redaction risks.

### GitHub and operational status

The existing stored user authorization successfully read installation and run
metadata for Shyamsundar0606/CodeMate-AI. Failure-filtered run listing returned zero
accessible failed runs and has_next=false. The historical successful run remained
successful. Therefore real GitHub-backed failure diagnosis remains unverified;
fixture-based success is not presented as live GitHub failure success.

The existing GitHub App permissions, credentials and backend/.env were preserved.
Model defaults are added only to the public backend environment example. Existing
migration revisions were not rewritten. Both codemate-postgres (5433) and
voxhire-postgres (5432) remained running; no VoxHire reset/change was performed.
Only separate disposable CI validation containers were removed. E2E-owned API8001
and frontend3000 processes/accounts were cleaned by the guarded runner.

CI workflow main.yml is unchanged: pinned lock installation, isolated PostgreSQL,
Alembic, warnings-as-errors Pytest, Ruff, npm ci, unit tests/lint/typing/build and
contents:read. Linux backend verification used the exact workflow commands with a
fresh isolated service; no local env files/model server/GPU/credentials were needed.
A new GitHub-hosted workflow run was not triggered because no commit/push was made.
The dependency graph required compatible websockets 16.1.1 for LangGraph SDK's
<17 constraint; the updated lockfile passed Windows and Linux installs/pip check.
Next.js and frontend dependency versions were unchanged. No force fixes, warning
suppression or test disabling was applied. No formal Python advisory audit is claimed.

### Corrected verification failures and limitations

An initial fixture expected metadata for extra jobs not available in the controlled
transport; missing resource evidence now yields a partial report rather than a
fabricated cause. A recovery test needed fresh session state before simulating a
second interruption. Initial type/test import and Windows punctuation issues were
fixed. jsdom lacks native summary Enter expansion, so unit tests verify focus/click
and real Edge verifies keyboard activation.

One browser run was started before Pytest exited, sharing the test database; it
was invalid and produced two failures. Both suites were rerun sequentially, and the
final complete results above pass. The first Linux harness used a read-only mount,
causing Ruff/Pytest cache errors under warnings-as-errors. It was corrected to a
writable temporary checkout matching GitHub runners; no warning was suppressed.

Limits: first bounded job page only (maximum four jobs); small-model quality;
syntactic reference/quote grounding does not prove all prose; imperfect redaction;
cooperative cancellation may wait for in-flight inference/network timeout;
manual worker lifecycle; at-least-once job-level recovery rather than exactly-once
node checkpointing; worker-driven retention does not delete external backups;
Edge desktop/mobile coverage is not a complete browser/security audit.

Read docs/AI_DIAGNOSTICS.md for architecture, API contracts, illustrative structured
report and exact Windows startup/test commands. Milestones 6 and 7 have not started.
No changes were committed or pushed. Git baseline remains 2e3239c.

### Files created

- `backend/alembic/versions/0003_ai_investigations.py`
- `backend/app/ai/__init__.py`
- `backend/app/ai/errors.py`
- `backend/app/ai/evidence.py`
- `backend/app/ai/graph.py`
- `backend/app/ai/schemas.py`
- `backend/app/ai/worker.py`
- `backend/app/api/routes/ai.py`
- `backend/app/integrations/ollama/__init__.py`
- `backend/app/integrations/ollama/client.py`
- `backend/app/models/ai_investigation.py`
- `backend/app/services/ai_investigation_service.py`
- `backend/scripts/ai_worker.py`
- `backend/scripts/verify_local_ai.py`
- `backend/tests/ai_mock.py`
- `backend/tests/test_ai.py`
- `docs/AI_DIAGNOSTICS.md`
- `frontend/src/app/(protected)/dashboard/ai/investigations/[id]/page.tsx`
- `frontend/src/app/(protected)/dashboard/ai/page.tsx`
- `frontend/src/components/ai/diagnostics.tsx`
- `frontend/src/lib/ai.ts`
- `frontend/src/tests/ai.test.tsx`

### Files modified

- `README.md`
- `backend/.env.example`
- `backend/alembic/env.py`
- `backend/app/core/config.py`
- `backend/app/core/logging.py`
- `backend/app/main.py`
- `backend/app/models/__init__.py`
- `backend/requirements-dev.lock.txt`
- `backend/requirements.txt`
- `backend/tests/test_database.py`
- `docs/ARCHITECTURE.md`
- `docs/GITHUB_INTEGRATION.md`
- `docs/PROGRESS.md`
- `docs/WINDOWS.md`
- `frontend/e2e/workspace.spec.ts`
- `frontend/next-env.d.ts`
- `frontend/scripts/e2e_backend.py`
- `frontend/src/app/globals.css`
- `frontend/src/components/dashboard/dashboard-shell.tsx`
- `frontend/src/components/github/investigation.tsx`
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/auth/session.ts`
- `frontend/src/tests/session.test.ts`

## 2026-10-13 - Investigation refresh feedback fix

The report's Refresh investigation handler discarded the refetch result and had
no explicit feedback. A successful GET returning identical completed data therefore
appeared to do nothing. A refetch failure could also replace the cached report
with the page-level error state.

Updated `frontend/src/components/ai/diagnostics.tsx` to announce
"Refreshing investigation..." during refresh and "Investigation updated" after
success, including unchanged responses. The button is temporarily disabled during
fetching. Failed refreshes retain the last loaded report and display a useful
error with a retry option. The polite live region supports screen-reader feedback;
keyboard activation remains available. Refresh uses the existing authenticated GET
only and does not restart, retry, or reanalyze investigations. Backend JWT, cookie,
CSRF, ownership, and authorization behavior is unchanged.

Added four regression tests in `frontend/src/tests/ai.test.tsx` covering unchanged
completed data, changed data, loading/keyboard behavior, and API error recovery.
Existing pending local-model button changes and generated Next.js type references
were preserved. No unrelated application code was changed.

Verification results:

- Backend: 191 tests passed with warnings treated as errors (`pytest -q -W error`).
- Frontend: all 106 unit tests passed.
- Ruff lint passed; formatting check reported 74 files already formatted.
- ESLint passed with zero warnings; TypeScript verification passed.
- Next.js production build passed using the existing isolated `.next-e2e` output
  configuration; the original `next-env.d.ts` contents were restored afterwards.
- Real Microsoft Edge verification passed with a disposable account and the
  existing guarded PostgreSQL test setup. The browser used the real frontend and
  isolated authenticated backend, with controlled GitHub/Ollama test fixtures.
  A completed successful investigation (attempt 1, no failure detected, no model)
  returned HTTP 200 through a single GET. Keyboard activation showed loading and
  disabled-button states, then success feedback. Report data remained identical;
  no refresh POST or JavaScript page errors occurred.
- A simulated browser network failure displayed the error/retry state while
  retaining the report; retry through the real test backend recovered successfully.
- The temporary test API and disposable account were cleaned up. A read-only
  snapshot comparison confirmed the existing personal investigation's status,
  stage, attempt count, report hash, and completion timestamp remained unchanged.

Verification against the user's exact owner-authenticated investigation page
remains **pending**, as requested. No personal browser session was accessed.
No commits or pushes were made, and Milestone 6 was not started.

## 2026-10-13 - Start investigation form investigation and feedback

Checked the development database read-only before submitting: no investigation
matched Shyamsundar0606/CodeMate-AI, installation 170278743, run 38441490639.
No live investigation was created and no existing development report was changed.

The original form was tested before editing in a disposable Microsoft Edge
session against the guarded test backend. The exact supplied identifiers passed
native validation and generated POST /api/v1/auth/ai/investigations. The disposable
account correctly received an authorization error for that live repository.
An authorized controlled failed-run fixture navigated successfully with the original
code. No JavaScript page errors occurred. These results do not establish the cause
of the user's original live-account symptom, and HMR was not identified as its cause.
A request for the user's visible error/HTTP status remains unanswered.

Confirmed feedback gaps were addressed only in AIOverview:

- Persistent native-validation feedback when the browser prevents submission.
- Accessible loading and accepted-response announcements, plus an explicit report
  link if navigation is delayed, and a history refresh after acceptance.
- A synchronous submission guard and disabled button after acceptance prevent
  repeated POSTs while pending or awaiting navigation.
- Actionable errors point to GitHub authorization and advise checking history after
  timeouts before manually resubmitting. POSTs are never automatically retried.
- Repository inputs are trimmed; numeric IDs are bounded to safe positive integers.

Authentication, session locking, CSRF bootstrap, backend authorization, ownership,
worker lifecycle, GitHub permissions, and backend idempotent creation are unchanged.
Existing backend tests cover same-run reuse, concurrent creation and admission.
Four new frontend regressions cover invalid forms, the exact large identifiers,
loading/rapid clicks, success fallback, and API failure recovery. Existing pending
local-model/refresh changes and next-env.d.ts contents were preserved.

Real Edge verification after the change passed: persistent validation with no POST,
visible authorization errors, disabled/loading feedback, one POST on rapid double
click, real authenticated navigation, and reuse of the same report on resubmission.
The fixture used controlled GitHub/Ollama transports and the isolated test database;
it does not verify live GitHub access for the user's account. Zero page errors.
Temporary test server and account were cleaned up before backend tests.

Frontend: 110 tests passed; ESLint with zero warnings passed; TypeScript passed;
Next.js production build passed in the supported isolated output directory. The
first type/build check caught unsupported Testing Library query options in the new
tests; those options were corrected before the successful reruns. Ruff lint passed
and formatting reported 74 files already formatted.
The first backend run had 190 passes and one fixture-setup PostgreSQL connection
timeout during a prolonged execution pause; the full warnings-as-errors suite was
rerun. Its final result is recorded below.

The reported exact live-account failure remains unconfirmed. The supplied live
workflow was not submitted from a personal session. No credentials were modified,
no commits/pushes were made, and no milestone beyond 5 was started.

Backend final verification limitation: the rerun tool session became unavailable
before its result could be retrieved. A subsequent verifiable full attempt ended
with 191 fixture-setup errors in 9.08 seconds. PostgreSQL was no longer listening
on 5433, and the Docker Desktop Linux engine pipe was unavailable. Therefore the
backend suite is **not passing in this verification session**. The earlier run's
190 passes / one database timeout must not be presented as a complete pass. No
backend tests were disabled and no database/container settings were changed to
work around this outage. Restore Docker/PostgreSQL and rerun `pytest -q -W error`
to complete backend verification.

Files changed for this task: `frontend/src/components/ai/diagnostics.tsx`,
`frontend/src/tests/ai.test.tsx`, and `docs/PROGRESS.md`. The preexisting generated
`frontend/next-env.d.ts` change was preserved. Git diff whitespace check passed.


## 2026-10-14 - Milestone 6 local voice agent

Implementation is ready for review. Physical microphone capture, audible speaker
output, actual GPU operation, real French speech input and personal live GitHub
voice verification remain pending. These are not completed checks.

Started from clean main at 5193d57. Created feature/milestone-6-voice-agent while
preserving test/ai-failure-diagnosis and the existing stash. GitHub workflow files
were unchanged. No failing workflow was merged, no commit/push/merge or branch/stash
deletion occurred, no .env was overwritten, and Milestone 7 was not started.

Added /dashboard/voice and its sidebar entry: typed commands, explicit native
push-to-talk, permission/duration/stop/cancel handling, editable English/French/Auto
transcripts, grounded replies, validated internal links, saved conversation context,
explicit investigation confirmation and Piper Play/Pause/Stop/Replay. Starting a
new request stops prior playback. Expired confirmations return actionable errors
and can be dismissed. Existing JWT, cookie ownership, origin, session expiry and
CSRF protections apply to all mutations, including raw binary audio uploads.

Speech uses official Windows wheels: faster-whisper 1.2.1, CTranslate2 4.8.3,
PyAV 19.0.1, Piper 1.8.0 and ONNX Runtime 1.31.0. CPU int8 is default. Detection and
initialization failures fall back to CPU. Lazy serialized subprocess workers reuse
models and terminate on timeout. Audio is bounded by bytes, MIME/container checks,
duration, decoded samples and upload time. The API does not persist audio. CI does
not download model weights. No separate FFmpeg or external Piper executable is
required. User-approved model setup downloaded official Whisper base and
LJSpeech medium; pinned revisions/hashes, model card and repository README are
retained under ignored models/. Dataset public-domain status, repository MIT
metadata and Piper GPL-3.0-or-later obligations are documented separately.

The bounded typed LangGraph uses deterministic known intents and schema-validated
local Ollama variations. Tools reuse existing authorized GitHub/investigation
services. No model-generated API paths, IDs, SQL, external URLs or shell commands
can execute. Ambiguous repository lookup asks for clarification; selecting another
repository clears previous workflow context. Facts come from GitHub responses or
owned saved reports; general knowledge is labeled separately. CI logs open through
the existing secure viewer and are not spoken wholesale.

Additive migration 0004_voice_agent adds VoiceSession, VoiceTurn, VoiceAction and
VoiceBudget, preserving previous tables/data. Context is owner-scoped with fixed
expiry, 20-turn retention and opt-in transcript storage. Pending actions hold exact
targets and short expiry. Voice-only yes cannot execute. Confirm rechecks owner,
active app session, original GitHub connection and workflow identity/status.
PostgreSQL session advisory locks survive service commits; replay is rejected and
existing investigation idempotency prevents duplicate creation. Rate limits are
durable; model concurrency assumes one API worker. Expired data is removed on the
owner's next mutation; idle expired records/backups need separate retention.
Redaction is imperfect, so users should review summaries before sharing/speaking.

### Verification evidence

Final frontend: 136 Vitest tests passed, including all original 110. ESLint passed
with zero warnings; TypeScript and Next.js 16.4 production build passed. Ruff,
pip check and Alembic check passed. Earlier complete backend runs passed 235 then
236 tests; the final run including the repository-switch regression is recorded
below. Migration regressions preserve users, connections and investigations.
No existing tests were removed, skipped or weakened for a green result.

Real local smoke: Piper generated 128556 WAV bytes. CPU faster-whisper returned
"code mate, open my GitHub repositories." Real Qwen2.5-Coder interpreted a natural
profile-navigation phrase. Python 3.12.10 reported CPU int8/int8_float32/float32
support. The existing CodeMate PostgreSQL startup helper passed on port 5433.

Real Edge integration used real local models, synthetic microphone input and
controlled GitHub fixtures. MediaRecorder produced browser audio; Whisper returned
"Code Mate, analyze the latest failed pipeline." Authorized fixture run 701 was
reported as failed. No investigation existed before Confirm; Cancel created none.
A double click sent one confirmation POST and created one investigation, returning
/dashboard/ai/investigations/00b3af80-910f-4afb-bc9e-45938fd34056.
Piper audio decoded and advanced playback in Edge (6.757007 seconds). Play, Pause,
Stop and Replay passed. History restored after reload; JavaScript page errors: zero.
Desktop/mobile screenshots were visually reviewed and a 390px overflow check passed.
These results do not establish personal live GitHub or physical audio verification.

A test-only GitHub identity collision was fixed with unique identities per E2E
prefix. The helper now has a __main__ guard for Windows speech-worker spawning.
A prolonged execution pause stopped local services; Docker Desktop was restored
through its installed executable and only CodeMate's PostgreSQL helper was used.
Disposable accounts, owned servers and owned speech workers were cleaned up.
No other project's containers, ports or files were changed.

### File manifest

New backend files:

- app/voice/__init__.py, agent.py, errors.py, schemas.py, speech.py
- app/models/voice.py; app/services/voice_service.py; app/api/routes/voice.py
- alembic/versions/0004_voice_agent.py
- scripts/setup_voice_models.py; scripts/verify_voice_local.py
- tests/test_voice.py

New frontend files:

- src/app/(protected)/dashboard/voice/page.tsx
- src/components/voice/assistant.tsx; src/lib/voice.ts; src/tests/voice.test.tsx
- scripts/verify-voice-browser.mjs
- AGENTS.md, automatically generated by Next.js dev and retained for user review

Modified files:

- .gitignore; README.md
- backend/.env.example; requirements.txt; requirements-dev.lock.txt
- backend/app/core/config.py; app/main.py; app/models/__init__.py
- backend/tests/test_database.py (expected new additive migration head)
- frontend/scripts/e2e_backend.py; src/app/globals.css
- frontend/src/components/dashboard/dashboard-shell.tsx
- frontend/src/lib/api/client.ts; src/lib/auth/session.ts; src/tests/session.test.ts
- docs/ARCHITECTURE.md; docs/WINDOWS.md; docs/PROGRESS.md

Models, manifests and synthetic audio/screenshots are ignored local artifacts.
Generated next-env.d.ts was restored to the clean initial baseline. WINDOWS.md
contains setup/startup/test commands, licensing, troubleshooting and manual checks;
ARCHITECTURE.md contains API contracts and security/retention bounds.

Final verification: all 239 backend tests passed with warnings treated as errors
(191 original plus 48 new). All 136 frontend tests passed (110 original plus 26 new).
Final Ruff, formatting, ESLint, TypeScript, production build, pip check and Alembic
check passed. Hardware, actual GPU/French speech and personal GitHub checks remain
pending as listed above. No commits or pushes were made.

Final target-selection review distinguishes explicit latest-failed searches from
references to the previously identified workflow. A temporary strict-intent-schema
regression and an incomplete successful-run fixture were corrected; the final full
run passed all 239 tests. Hosted LangGraph tracing is disabled, matching Milestone 5,
with a privacy regression. No automated test failures remain.
A concurrent user-only whitespace edit to frontend/postcss.config.mjs was preserved
and was not changed by this implementation.


## 2026-10-14 - Milestone 6 final Git review and commit preparation

The owner reports real-device verification of microphone transcription, Piper
speaker playback, personal GitHub workflow lookup, and AI investigation completion.
These four checks are now recorded as **user-verified** from the commit-preparation
request. They were not independently repeated by Codex in this review. No new
transcript, run ID, investigation ID, model/device details, or timing evidence was
provided, so none is invented. The earlier pending notes describe the implementation
session and are superseded for these four checks by this update.

Physical-device recording cancellation and live pending-investigation cancellation
were not explicitly confirmed by the owner and remain pending. Automated frontend
and backend cancellation regressions and the previous controlled Edge cancellation
check passed. Cancelling before upload discards the recording. Cancelling during
transcription aborts the browser request and ignores its result; audio may already
have reached the backend, and active inference may continue until completion or
its configured timeout. The current UI cancellation notice does not distinguish
those stages, a known wording limitation rather than proof of server cancellation.
Actual GPU acceleration and real French speech recognition remain unverified.

Reviewed tracked modifications and untracked Milestone 6 files. Migration
0004_voice_agent upgrades from 0003 by creating only four voice tables and their
indexes/foreign keys; it does not rewrite or drop prior tables. Alembic check
reported no pending schema operations. GitHub repository/workflow/log operations
remain GET-only, with existing installation permission validation rejecting
non-read permissions. OAuth token operations retain their existing behavior.
Voice-only yes cannot create an investigation: stored pending actions and the
explicit confirmation endpoint enforce owner/session/CSRF checks, original
connection and workflow revalidation, expiry, replay rejection and idempotency.

Secret review scanned 194 tracked/untracked text files before this documentation
update. No matches for actual local secret values or high-confidence credential
patterns were detected; no values were printed. A tracked-path audit found no
private .env/key files, model weights, audio recordings, logs or caches. Expected
public test credentials and example placeholders are not production secrets.
Existing ignore rules cover local environments, speech weights, verification
artifacts, dependency/build caches and logs. No sensitive artifacts are in the
proposed allowlist.

frontend/postcss.config.mjs is the concurrent user whitespace/newline edit and is
preserved unchanged, excluded from staging. frontend/next-env.d.ts contains only
Next.js-generated development route type imports; it is preserved and excluded.
frontend/AGENTS.md matches the installed Next.js automatic agent-rules generator,
which runs during next dev when a coding agent is detected. It contains generic
tooling guidance, not Milestone 6 application behavior. Recommend excluding it
from this milestone commit and considering it separately; leave the file intact.
It may be regenerated on later development starts. No .gitignore changes were
made to hide it, and no file was deleted or reset.

No implementation files were changed during this final review. Current review
checks: Ruff lint and formatting passed (87 files); Alembic and pip checks passed.
Frontend checks and final whitespace/index verification are recorded below when
complete. The full 239-backend/136-frontend implementation results remain distinct
from review checks. No staged paths existed when this review began. No staging,
commit, push, merge, reset, stash/branch deletion or Milestone 7 work was performed.

### Exact proposed staging allowlist (35 files)

Only these individual paths are proposed. Do not use git add . or git add -A.
The allowlist includes this updated progress file and excludes the three files
listed above. No staging command has been executed.

```text
.gitignore
README.md
backend/.env.example
backend/alembic/versions/0004_voice_agent.py
backend/app/api/routes/voice.py
backend/app/core/config.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/voice.py
backend/app/services/voice_service.py
backend/app/voice/__init__.py
backend/app/voice/agent.py
backend/app/voice/errors.py
backend/app/voice/schemas.py
backend/app/voice/speech.py
backend/requirements-dev.lock.txt
backend/requirements.txt
backend/scripts/setup_voice_models.py
backend/scripts/verify_voice_local.py
backend/tests/test_database.py
backend/tests/test_voice.py
docs/ARCHITECTURE.md
docs/PROGRESS.md
docs/WINDOWS.md
frontend/scripts/e2e_backend.py
frontend/scripts/verify-voice-browser.mjs
frontend/src/app/(protected)/dashboard/voice/page.tsx
frontend/src/app/globals.css
frontend/src/components/dashboard/dashboard-shell.tsx
frontend/src/components/voice/assistant.tsx
frontend/src/lib/api/client.ts
frontend/src/lib/auth/session.ts
frontend/src/lib/voice.ts
frontend/src/tests/session.test.ts
frontend/src/tests/voice.test.tsx
```

### Proposed commit message

```text
feat: add fully local voice agent for Milestone 6

Add local Whisper transcription, Piper speech and a bounded LangGraph agent.
Reuse authorized read-only GitHub tools with expiring explicit investigation
confirmation, replay protection and owner-scoped PostgreSQL conversation state.
Add the dashboard voice interface, additive migration, tests and Windows setup.
Document user-verified real-device/live GitHub results and remaining checks.
```

Remaining operational limits: bounded repository/run lookup pages, one API worker
for practical model memory/concurrency, idle expired metadata cleanup on the next
owner mutation, imperfect redaction, and applicable Piper/model distribution
license notices. No new deployment or GitHub write capability is introduced.

Final review verification: frontend unit suite rerun passed all 136 tests; ESLint
with zero warnings and TypeScript passed. Ruff lint/format (87 files), Alembic
check and pip check passed. No implementation files changed, so backend Pytest
and the production build were not repeated during this documentation-only review;
their last complete implementation results were 239 passed and a successful build.
Git diff whitespace check passed, the index is empty, and the exact 35-file
allowlist excludes PostCSS, next-env.d.ts, AGENTS.md and all private artifacts.
Nothing was staged. Committing still requires the owner's approval.


## Milestone 7: secure developer automation review delivery (2026-10-17)

### Repository audit and implementation scope

Verified clean local main and remote refs/heads/main at
302f3f4d96796c66f63f4a97dc12f94f990603c4 before editing. Created
feature/milestone-7-safe-automation from that commit. Both existing stashes were
preserved. No commit, push, merge, reset, branch deletion or stash operation was
performed. PostCSS configuration, next-env.d.ts and existing user/generated files
were not changed for this milestone. Existing GitHub Actions workflows and all
Python/npm dependency files are unchanged.

Implemented the explicitly permitted proposal-first scope. The system can inspect
authorized source, explain code, retrieve bounded real CI metadata/log evidence,
generate and validate small proposals, show exact diffs, and persist explicit
review decisions. A verified execution sandbox is unavailable, so patch
application and command execution are hard-disabled. No host checkout/workspace
is created; no repository code is executed on the Windows host. This is not a
completed isolated runner or autonomous code-repair service.

### Features and architecture

- Authenticated /dashboard/automation with installation/repository selection,
  exact selected source paths, optional workflow ID, pinned snapshot context,
  explanation/patch requests, evidence citations, changed-file list, unified diff,
  risks, confidence and expiry. Native confirmation dialog supports keyboard
  interaction, loading feedback, visible errors, review approval, rejection and
  cancellation. Text mode does not require a microphone.
- Reuses GitHubRepositoryService installation membership and user authorization,
  existing local Ollama settings/client, bounded LangGraph, JWT refresh/CSRF and
  owner advisory locks. GitHub access remains read-only. Generated text has no
  command, tool, filesystem or execution authority.
- Backend-generated diffs use typed full-file replacements only for inspected
  existing regular text blobs. Git blob integrity, exact commit SHA, SHA-256 base
  hashes, size/type/path restrictions, case collision checks and exact citation
  matches are enforced. No raw LLM patches are applied. Secret-like content is
  rejected/redacted; detection cannot guarantee all private data is recognized.
- UUID request idempotency for snapshots and successful proposal retries;
  concurrent duplicate review decisions serialize and replay fails. Review binds
  owner, workspace, original GitHub connection, repository, revision, complete
  patch-content hash, validation template IDs and expiry. Voice-only approval is
  insufficient. New voice phrases navigate to the automation review page only.
- Six mutations/minute/user, ten unexpired snapshots/user, five proposals/session,
  four source files, 12 KB/file, 24 KB source total and a bounded 5,000-entry Git
  tree. One local generation slot and a 90-second Ollama deadline. No paid service,
  new dependency or automatic model download was introduced.

### Database changes and retention

Additive 0005_safe_automation follows 0004_voice_agent and creates only
four new tables: automation_sessions (logical snapshot workspace/context),
automation_proposals (typed proposal and exact review record), automation_audit
(event types/timestamps) and automation_budgets (owner mutation quota). New
foreign keys, indexes, unique request IDs and proposal-state constraint support
isolation and replay protection. Existing milestone tables are not rewritten.

Snapshots/associated evidence expire after 24 hours; proposal review expires
after 30 minutes. Approval metadata records at most a five-minute review grant,
not reusable execution authorization. The owner's next mutation removes expired
sessions and their cascading metadata; idle expired rows/backups can persist
until maintenance/backup expiry. Private source and small redacted log excerpts
are stored only as needed for review. No GitHub tokens, model credentials, raw
audio, execution output or invented test results are stored by this feature.
The development database was not migrated during verification. Apply the new
head with the documented Windows startup command before running the new backend.

### Automated verification performed

- Backend full suite: **304 passed** with warnings treated as errors, including
  the previous 239 tests and 65 new automation cases. Final command:
  .venv/Scripts/python.exe -m pytest -q -W error (from backend).
- Ruff lint passed; Ruff format check passed for 95 backend Python files.
  The separate optional browser fixture also passed Ruff and formatting checks.
- Alembic current on the guarded test database: 0005_safe_automation (head).
  Alembic check: no new upgrade operations. Full regression suite verified
  downgrade/upgrade consistency and preservation of existing user/session and
  investigation records. No development downgrade or destructive migration ran.
- Frontend: **145 passed**, including all previous 136 tests and nine new
  automation regressions. ESLint passed with zero warnings, TypeScript passed,
  and the production Next.js 16.4.0 build passed including /dashboard/automation.
- pip check: no broken requirements. Existing CI-compatible commands were used;
  a remote GitHub Actions run was not triggered because nothing was pushed.
- Initial development checks exposed an ESLint account-reset effect issue and
  migration metadata drift while the request-ID schema was changing. The account
  boundary now remounts the workbench by owner. The final full backend suite ran
  against a stable schema and passed. No tests were disabled or weakened.
- Secret review scanned 208 tracked/new source candidates against high-confidence
  patterns and actual local secret values in memory: no credential matches.
  Credential/model/audio/log/cache artifacts remain ignored; examples contain
  disposable public test settings only. No files were staged.

Security regressions cover unauthenticated/CSRF/origin denial, cross-user and
unauthorized repository access, path traversal/absolute/drive/ADS/reserved/sensitive
paths, symlink/submodule/executable Git entries, tree truncation/case collisions,
blob integrity/size, raw-hunk/command injection, exact base/hash binding, grounded
citations, prompt-injection text without tool authority, expiry/replay/concurrent
review, persisted-state tampering, network-retry duplicates, CRLF/no-final-newline
handling and database failure without approval. Execution-denial cases cover
network/host/resource/shell/restart/cancellation requests. These prove denial,
not actual sandbox isolation properties.

### Real local verification and remaining manual checks

Real Microsoft Edge with the actual production frontend and FastAPI, a disposable
account and guarded test DB verified source inspection, exact diff preview,
rejection, explicit review approval, persisted history after reload, secret-path
rejection and voice navigation. GitHub and Ollama upstreams were controlled test
fixtures in that browser flow; it did not use a personal browser or credentials.
The browser observed zero JavaScript errors and zero execution requests.
Desktop and 390px mobile screenshots were inspected; the mobile title layout
was corrected and the final browser rerun confirmed no horizontal overflow.

Separately, real local qwen2.5-coder:3b produced a schema-valid, exact-source-cited
explanation of backend/app/api/health.py from committed main 302f3f4 with zero
changes. It also produced a validated one-file patch for a controlled addition
example with one grounded citation. Neither smoke applied a patch or ran tests.
This does not establish repair correctness for arbitrary real CI failures.

Physical microphone/Piper playback were historical Milestone 6 checks, not
repeated here. Existing voice regressions passed and the new typed voice command
was verified in Edge. A personal GitHub end-to-end repair proposal, real failed-CI
fix quality, GPU/French speech and physical cancellation remain unverified in
this milestone. Browser tests use synthetic upstreams and deterministic evidence.

Patch application, actual validation exit codes/output, execution cancellation,
resource exhaustion controls, no-network/host isolation and real Windows
junction/reparse-point containment remain deferred. No filesystem is materialized
by the proposal-only API. A future narrow developer runner must verify those
properties and require fresh execution approval before enabling code execution.
In-flight synchronous model generation has a timeout but cannot be recalled by
leaving the page. Source selection is explicit; automatic whole-repository code
indexing is not implemented. Large repositories and unsupported paths fail closed.

### Windows startup and review

See docs/WINDOWS.md, Milestone 7 section, for CodeMate-only PostgreSQL startup on
5433, additive Alembic upgrade/check, existing Ollama readiness, backend/worker/
frontend startup and all verification commands. Optional browser command after a
production build: node scripts/verify-automation-browser.mjs from frontend, with
ports 3000/8001 free and no concurrent Pytest. It cleans only its own disposable
account and child processes. No existing personal browser is accessed.

### Exact Milestone 7 changed files (uncommitted)

```
README.md
backend/alembic/versions/0005_safe_automation.py
backend/app/api/routes/automation.py
backend/app/automation/__init__.py
backend/app/automation/graph.py
backend/app/automation/policy.py
backend/app/automation/schemas.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/automation.py
backend/app/services/automation_service.py
backend/app/voice/agent.py
backend/app/voice/schemas.py
backend/tests/test_automation.py
backend/tests/test_database.py
docs/ARCHITECTURE.md
docs/PROGRESS.md
docs/WINDOWS.md
frontend/scripts/automation_fixture.py
frontend/scripts/verify-automation-browser.mjs
frontend/src/app/(protected)/dashboard/automation/page.tsx
frontend/src/app/globals.css
frontend/src/components/automation/workbench.tsx
frontend/src/components/dashboard/dashboard-shell.tsx
frontend/src/lib/api/client.ts
frontend/src/lib/auth/session.ts
frontend/src/lib/automation.ts
frontend/src/lib/voice.ts
frontend/src/tests/automation.test.tsx
```

No commit or push is authorized by this implementation request. Review the
proposal-only delivery and documented limitations before any publication.


### Milestone 7 citation contract review ? 2026-10-18

The previous model schema accepted free-form `source` and `quote` strings. The
LangGraph validator then required the model's path to equal a retrieved source
key and its quote to be an exact substring. It supplied no enumerated evidence
IDs or source-line ranges, leaving the model to reproduce identifiers and text.
Invalid output was not saved, and the audit deliberately retained only a generic
failure category. The original rejected citation cannot be recovered safely from
those records. A bounded reproduction with the exact developer request supplied
by the user passed under the old contract (two known full paths and exact quotes);
therefore the precise original offending value and whether it was a path or quote
mismatch remain unconfirmed. Do not describe that nondeterministic failure as a
reproduced file-path, line-range, or schema-reference error.

The new contract provides a deterministic, bounded catalog of exact pinned source
and CI excerpts, each with an evidence ID, source key and literal line range.
Ollama's structured schema enumerates only IDs from that snapshot. The model
selects IDs; the backend supplies the original path, quote and range. Unknown IDs,
model-authored paths, missing/duplicate references and incorrect supplied ranges
are rejected without remapping to other evidence. JSON whitespace and a single
anchored JSON Markdown fence are supported without repairing citation data.
Oversized catalogs fail closed instead of silently truncating source evidence.
Errors use AUTOMATION_CITATION_INVALID with safe retry guidance and no raw output.
There are no automatic model retries. The existing 90-second deadline, generation
budgets, authorization, source/credential scanning, audit logging and proposal-only
execution policy remain in place. Earlier persisted source/quote citations still
load; no migration or rewrite of stored proposals was performed.

Verification for this change:

- Full backend Pytest: 374 passed with warnings as errors. The automation subset
  passed 135 tests. New cases cover valid IDs, invented IDs, incorrect paths,
  missing/duplicate citations, invalid/typed line ranges, pretty/fenced JSON,
  exact CRLF/long-line excerpts, bounded catalogs and persisted GET restoration.
  Existing ownership, CSRF, credential, protected-path and disabled-execution
  security regressions passed.
- Full frontend unit suite: 155 passed, including ID/range display, Reload session
  without another POST, and legacy persisted citation compatibility.
- Backend Ruff lint and formatting passed (97 files); the updated optional browser
  fixture separately passed Ruff lint and formatting. Its path-dependent helper
  import was moved inside main so importing the fixture is lint-clean.
- ESLint with zero warnings and TypeScript verification passed.
- Next.js 16.4.0 production build passed in a disposable frontend copy without
  environment files. The active development server and concurrent next-env.d.ts
  edit were preserved.
- Real qwen2.5-coder:3b completed the exact supplied request in about 21 seconds
  through the authenticated FastAPI proposal API. The two source files came from
  the existing authorized pinned snapshot, read in a development-DB read-only
  transaction. Test account authorization/GitHub upstreams used controlled
  fixtures; real Ollama and guarded PostgreSQL test storage were used. HTTP 200,
  explained status, exact excerpt/range checks, database persistence, identical
  Reload-session GET, and an idempotent repeat with only one model call passed.
  Only the disposable account was removed afterward; personal snapshots and
  proposal data were not changed.

Limits: the real model selected eight valid excerpts from config.py, despite the
prompt's preference for one to three, and did not select main.py evidence. Its
explanation mentioned create_app and Settings. Exact provenance checks establish
where quoted evidence came from; they do not establish semantic support for every
statement in generated prose. The UI continues to label the suggestion unverified.
This check must not be reported as proof of complete citation coverage or factual
correctness of the generated explanation. No personal authenticated browser retest
or new real GitHub fetch was performed in this follow-up. To retest manually, inspect
the two files, select Explain source, paste the exact supplied developer request,
generate once, inspect the displayed sources/IDs/ranges, then click Reload session
and confirm the same saved explanation. Invalid references should display the safe
error and save no proposal. Patch application and test execution remain disabled.

Files changed in this follow-up (relative to its starting working tree):

- backend/app/automation/citations.py (new)
- backend/app/automation/graph.py
- backend/app/automation/schemas.py
- backend/tests/test_automation.py
- frontend/scripts/automation_fixture.py
- frontend/src/components/automation/workbench.tsx
- frontend/src/lib/automation.ts
- frontend/src/tests/automation.test.tsx
- docs/PROGRESS.md

Unrelated user changes were preserved. No commit, staging, push, merge, reset or
stash operation was performed.


## Milestone 7 final completion review, 2026-10-18

Final follow-up implemented per-file citation coverage, backend risk-hypothesis
labeling, a MEDIUM confidence ceiling, preserved review statuses after proposal
expiry and additional safe voice phrases. Existing implementation and stashes
were preserved. No execution capability or Milestone 8 work was added.

Verification: full backend 379 passed with warnings as errors; final automation
subset 140 passed; frontend 156 passed; Ruff, ESLint, TypeScript, pip check and
Alembic current/head/schema checks passed. Production build passed with the
existing CODEMATE_E2E isolated output option. The default .next output still
fails in the Turbopack CSS worker and was preserved. npm production audit reports
zero findings; the same five high development-tooling findings remain.

Actual Edge/FastAPI/PostgreSQL browser checks passed for explanation reload,
diffs, approval/rejection/cancellation persistence, history, safe navigation and
secret-path rejection. Screenshots were inspected on desktop and 390px mobile;
no page errors, horizontal overflow or execution requests occurred. Extended
coverage respects the existing six-mutation/minute limit by waiting for reset.

Real GitHub installation membership and both requested blobs passed integrity and
source-scanning checks at commit 302f3f4d96796c66f63f4a97dc12f94f990603c4.
This used a read-only transaction, not a new personal browser snapshot. Real
Qwen produced a valid one-line arithmetic patch in 40.84s. The exact two-file
explanation failed closed on missing main.py evidence (85.06s); after prompt
refinement it timed out (90.03s). No failed suggestion was saved. A successful
real two-file explanation and personal browser acceptance remain outstanding;
Milestone 7 is not declared fully finalized. Semantic correctness remains a
human-review responsibility even when evidence provenance passes.

See [the full final verification report](MILESTONE_7_FINAL_VERIFICATION.md) for
exact commands, migration status, security findings, limits, the complete staging
allowlist and remaining merge steps. Nothing was staged, committed or pushed.


## Milestone 7 remaining blockers resolved, 2026-10-18

Real two-file explanations now use bounded, file-local Qwen selection of
source-derived observations, preserving the original evidence IDs. No model
prose is synthesized into multi-file results. Backend rendering uses Python AST
facts within exact quoted source or explicitly extractive source prefixes;
request-focused selection avoids unrelated subjects when matching facts exist.
At most four calls, 192 output tokens per call, 35 seconds per call and 90 seconds
total are allowed, without retries. No partial proposal is saved on failure.
Single-file explanation and patch-generation behavior is preserved.

The exact two-file request passed against the saved real-source snapshot at
302f3f4d96796c66f63f4a97dc12f94f990603c4. Real local Qwen inference through the
JWT/CSRF-protected API completed in 1.42s with two calls and citations from both
files. PostgreSQL stored one proposal. GET Reload session and an unchanged
request-ID retry restored the identical proposal without further model calls.
The disposable API test used controlled GitHub authorization responses serving
the exact previously verified blobs; no personal login or snapshot was modified.

Default npm.cmd run build now passes with persistent production Turbopack-cache
reuse disabled. No manual generated-output removal or PostCSS edit was needed;
development caching and output-directory selection are preserved.

Final full backend suite: 394 passed in 181.67s with warnings as errors. Frontend:
158 passed; Ruff lint/format, ESLint, TypeScript, Alembic check and ordinary
production build passed. Both targeted blockers are closed; ready for commit
review. Existing stashes and generated-file edits remain. Nothing staged,
committed, pushed, merged or reset; execution remains disabled and Milestone 8
was not started. See MILESTONE_7_FINAL_VERIFICATION.md for exact commands,
limitations, current readiness and the updated staging allowlist.
