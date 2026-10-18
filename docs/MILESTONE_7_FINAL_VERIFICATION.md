# Milestone 7 blocker follow-up, 2026-10-18

This section supersedes the earlier blockers and results recorded below.

## Explanation diagnosis and fix

Reproduction command, from backend:
`$env:PYTHONPATH=(Get-Location).Path; .\.venv\Scripts\python.exe -u C:\Users\Shyam\AppData\Local\Temp\codemate_m7_explain.py`
The script reads the existing two-file snapshot in a read-only development DB
transaction and invokes the production graph with the exact requested question.
The original combined request reproduced AI_TIMEOUT at 90.03 seconds.
The old prompt combined both source catalogs, patch/replacement schema, risk
prose and up to 1,600 generated tokens in a 16,384-token context. The previous
coverage failure came from actual model-selected config.py-only citations;
coverage validation correctly rejected it. There were no automatic retries or
silent citation remapping. Timeout handling failed safely but did not solve the
oversized mixed task. No evidence was fabricated to make coverage pass.

Independent compact prose calls took 14.20s but still emitted unsupported and
unfinished claims. That intermediate approach was rejected. The final multi-file
explanation path uses one local model call per inspected file to select relevant
source-derived observations. Python observations are computed by ast.parse and
include only definitions, explicit bases, import modules, call sites and call
assignments visible within the exact cited excerpt. Whole required source lines
must occur in the quote, including when a long line is split into excerpts.
Other excerpts use a visibly extractive source-text prefix. Repository code is
never imported or executed. A lexical subject filter prefers observations naming
the user's subject when available; it does not manufacture semantic conclusions.
The model must select the original backend-issued evidence IDs. Every ID is
validated against that file's supplied subset of the original global catalog.
There is no renumbering, fallback citation attachment or second model synthesis.
Free-form explanation fields and unsupported security assertions are rejected.

The backend renders only the selected observations, grouped by file and labeled
with IDs. This is intentionally a compact source summary rather than an inference
about undocumented framework behavior. Exact source provenance does not establish
runtime behavior or security correctness. In particular, no claim about Pydantic
environment loading is inferred beyond the observed BaseSettings inheritance and
SettingsConfigDict use. Single-file explanations and patch generation retain their
existing paths and unverified-prose labels. Authentication, authorization, secret
scanning, hash binding and execution denial are unchanged; no migration needed.

Bounds: at most four calls, one per file, no automatic retries; 192 generated
tokens and an 8,192-token context per call; at most 35 seconds per call and 90
seconds shared wall-clock budget. Later calls use the remaining budget. Truncated
outputs, crowded contexts, invalid schemas, wrong-file IDs, no evidence and
expired budgets fail without a partial suggestion. Provider errors retain their
error code with file-specific no-save/retry guidance. The original user request
ID still binds the combined result to one persisted proposal.

Final real Qwen graph retest against commit
`302f3f4d96796c66f63f4a97dc12f94f990603c4`: 1.27 seconds, validated, LOW confidence,
no diff, exact citations from both requested files:

- config.py E0002: Settings inherits BaseSettings; model_config uses
  SettingsConfigDict, including its explicit call site.
- main.py E0047 and E0057: FastAPI imports and application construction using
  FastAPI, with other directly visible initialization calls in those excerpts.

The snapshot's two source files were verified against real authorized GitHub
blobs in the earlier run below. No new personal snapshot was created here.

Real authenticated API/persistence command, from backend:
`$env:PYTHONPATH=(Get-Location).Path; .\.venv\Scripts\python.exe -u C:\Users\Shyam\AppData\Local\Temp\codemate_m7_persistence.py`
This separate guarded script used a disposable test account with actual JWT login,
refresh cookies and CSRF, controlled GitHub authorization responses serving the
exact saved real-source blobs, real local Ollama, and dedicated PostgreSQL test
storage. It did not use or modify personal login sessions or source snapshots.

Results: snapshot POST 201; explanation POST 200 with explained status in 1.42s;
one persisted proposal; GET Reload session returned the identical result with
no additional inference; repeating the same request ID returned that same single
proposal, still exactly two model calls. Stored PostgreSQL suggestion content
matched the API response. The script removed only its exact disposable account
and cascading test records. No source files changed and execution remained disabled.

Provider metrics (warm qwen2.5-coder:3b): config file 0.72s, 277 prompt tokens,
18 generated tokens; main file 0.59s, 386 prompt tokens, 30 generated tokens;
both done_reason=stop. Backend-owned evidence IDs and exact ranges:

| File | Evidence ID | Lines |
| --- | --- | --- |
| backend/app/core/config.py | E0002 | 7-12 |
| backend/app/main.py | E0047 | 7-12 |
| backend/app/main.py | E0057 | 58-62 |

These ranges cover the actual class/configuration declarations, imports and
FastAPI application constructor. The model selects evidence rather than
asserting that every detail of the original question has been proven. Results
remain labeled LOW confidence with explicit runtime/framework limitations.
Cold model loading or a busy host may still hit the bounded actionable timeout.

## Default production build diagnosis and fix

`npm.cmd run build` reproduced the actual default .next Turbopack failure:
"Failed to write app endpoint /page", globals.css, and a CSS-worker Node process
exiting with code 0 before connection. Panic log:
`C:\Users\Shyam\AppData\Local\Temp\next-panic-8247e831139af72f472adc5f49a1a639.log`.
CIM inspection showed no running CodeMate Next.js process; the three existing
Node processes belonged to Codex tooling and were not terminated. Cache owner
was DESKTOP-24SVL0S\Shyam with modify access for the user/sandbox. Persistent
Turbopack cache dated back to 2026-10-11. Both default and isolated build worker
artifacts and installed Next configuration defaults were inspected.

The installed Next.js 16.4.0 enables persistent production Turbopack caching by
default. Setting experimental.turbopackFileSystemCacheForBuild=false in
frontend/next.config.ts makes the ordinary default .next build succeed. This
isolates persistent cache reuse as the failing path; the exact corrupt cache
record was not identified or edited. No manual removal, rename or cache-clearing operation was performed.
Existing cache files were preserved; ordinary build artifacts were regenerated. PostCSS is unchanged. Development caching and the
existing CODEMATE_E2E output selection are unchanged. Production builds trade
persistent-cache reuse for reliable fresh computation. Regression tests cover
both output-directory modes and unchanged development-cache defaults.

Default build command: `npm.cmd run build`, with CODEMATE_E2E unset.
Output: compiled in 5.0s, TypeScript passed in 8.8s, all 15 static pages generated,
automation route included. The pre-existing next-env.d.ts dev-types edit was
preserved after the build. No removal approval was needed because no output was
removed.

## Final checks and readiness

| Final command | Exact result |
| --- | --- |
| Backend `.\.venv\Scripts\python.exe -m pytest -W error` | 394 passed in 181.67s, warnings treated as errors |
| Backend `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| Backend `.\.venv\Scripts\python.exe -m ruff format --check .` | 100 files already formatted |
| Root Ruff formatting including optional browser Python fixture | 101 files already formatted |
| Backend `.\.venv\Scripts\python.exe -m alembic check` | No new upgrade operations detected |
| Frontend `npm.cmd test` | 10 test files, 158 passed in 41.76s |
| Frontend `npm.cmd run lint -- --max-warnings=0` | Passed, exit 0 |
| Frontend `npm.cmd run typecheck` | Passed, exit 0 |
| Frontend `npm.cmd run build`, default .next | Passed, all 15 static pages generated |
| `git diff --check` | Passed, only existing LF/CRLF normalization notices |

All requested blocker checks pass. Milestone 7 is ready for commit review on
feature/milestone-7-safe-automation, subject to explicit staging/commit approval.
There are no remaining blockers for the two requested items. The complete final
suite includes all prior tests plus the new observation-grounding, wrong-file ID,
no-retry/timeout/deadline/token/context bounds, split-line citation, persistence,
idempotency and build-config regressions.

Known limitations: multi-file summaries are structural source observations,
not inferred framework/runtime guarantees. Single-file and patch prose remains
explicitly unverified. Warm-model timings are not guaranteed on a cold or busy
host. Persistent production build caching is disabled. The five previously
reported high dev-tooling audit findings remain known; npm advisories were not
re-audited during this blocker follow-up. No fresh personal-browser acceptance
was performed here; real model inference and authenticated API persistence were
verified separately from the earlier fixture browser checks. None of these
limitations enables execution or expands scope beyond Milestone 7.

Both original stashes, all pre-existing changes and the expected feature branch
are preserved. Nothing staged, committed, pushed, merged or reset. No branch or
stash deletion; no Milestone 8 work; patch application and test execution remain
disabled. The complete updated staging allowlist is retained below and excludes
frontend/next-env.d.ts, environment files and generated output.

---

## Historical verification before the blocker fixes, 2026-10-18

Milestone 7 remains a proposal-and-review assistant. Patch application, repository
test execution, commits, pushes and deployment remain disabled. No Milestone 8
work was started. Automated checks pass, but final readiness is conditional on a
successful real two-file explanation and personal browser acceptance.

## Implementation and preservation

The existing implementation was inspected and retained rather than rebuilt.
This follow-up adds deterministic evidence coverage for explicitly named source
files and changed patch files, makes per-file evidence choices explicit in the
model prompt, labels generated risks as unverified hypotheses, caps HIGH model
confidence at MEDIUM, and clarifies the viewer's provenance-only guarantee.
Citation presence does not establish semantic relevance or prove model claims.
No repository-specific security conclusions are hardcoded.

Approved, rejected, cancelled and explained records retain their visible status
past proposal expiry while the parent session remains available. Pending proposals
still expire and cannot be approved. Safe voice navigation now also recognizes
"show the proposed patch" and "explain this repository". These only navigate.
The browser regression adds explanation reload and cancellation persistence.

Starting branch: feature/milestone-7-safe-automation. Starting state contained
17 modified tracked files and 17 untracked implementation files, with no staging.
Both stashes were inspected and preserved, including the PostCSS/generated-file
stash. frontend/next-env.d.ts retains its starting dev-types imports and is
excluded from the allowlist. PostCSS, credentials, ports and other projects were
not modified. Docker Desktop was started; only codemate-postgres is running.
No stage, commit, push, merge, reset, stash application or branch switch occurred.

Migration 0005_safe_automation already existed as an untracked additive migration
following 0004_voice_agent. It was retained, not recreated. Development migration
current/head and metadata checks pass. Test fixtures apply it to the guarded
dedicated codemate_test_db. No production-history migration or destructive cleanup
was performed. Existing session retention is still 24 hours; proposal review
expires after 30 minutes. Expired sessions are omitted from active history and
existing quota cleanup can delete them. This is bounded retention, not archival.

## Commands and results

Commands run from backend unless noted. Earlier results elsewhere in the docs
are historical; the following are results from this run.

| Command | Result |
| --- | --- |
| `.\.venv\Scripts\python.exe -m pytest -W error` | 379 passed in 230.58s |
| `.\.venv\Scripts\python.exe -m pytest tests/test_automation.py -W error` | Final follow-up: 140 passed in 62.70s |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m ruff format --check .` | 97 files already formatted |
| Root: `.\backend\.venv\Scripts\python.exe -m ruff check backend frontend/scripts/automation_fixture.py` | All checks passed |
| Root: corresponding `ruff format --check` | 98 files already formatted |
| `.\.venv\Scripts\python.exe -m pip check` | No broken requirements found |
| `.\.venv\Scripts\python.exe -m alembic heads` | 0005_safe_automation (head) |
| `.\.venv\Scripts\python.exe -m alembic current` | 0005_safe_automation (head) |
| `.\.venv\Scripts\python.exe -m alembic check` | No new upgrade operations detected |
| Frontend: `npm.cmd test` | 9 files, 156 tests passed in 15.93s |
| Frontend: `npm.cmd run lint -- --max-warnings=0` | Passed |
| Frontend: `npm.cmd run typecheck` | Passed |
| Frontend: `npm.cmd run build` | Existing default .next output fails in Turbopack CSS worker |
| Frontend: `$env:CODEMATE_E2E='1'; npm.cmd run build` | Passed, all 15 static pages generated, automation route included |
| Frontend: `npm.cmd audit --omit=dev` | 0 vulnerabilities, exit 0 |
| Frontend: `npm.cmd audit` | Existing 5 high dev-tooling findings, exit 1 |
| Root: `git diff --check` | Passed; Git emits LF/CRLF normalization notices |

The first sandboxed Vitest run failed to read temporary transformation files;
the unrestricted rerun passed all 156 tests. The default build failed both inside
and outside the sandbox; isolated .next-e2e production compilation passed without
altering PostCSS or deleting the original cache. No dependency changes, forced
audit fixes or downgrades were made. Five high development findings remain in the
braces/micromatch/fast-glob/Next ESLint dependency chain. No Python advisory audit
is claimed; pip check verifies dependency compatibility only.

## Real GitHub and local Ollama

A temporary verification script used the existing encrypted GitHub authorization
and a read-only development-database transaction. It checked installation
membership, fetched the pinned Git tree and both blobs through the real GitHub
API, checked regular-file mode, size and Git blob SHA-1, and scanned their source.

Commit: `302f3f4d96796c66f63f4a97dc12f94f990603c4`.

- backend/app/main.py: 5,962 bytes, accepted by source scanner, matches snapshot.
- backend/app/core/config.py: 10,126 bytes, accepted, matches snapshot.

No new personal snapshot, proposal or audit event was written by that read-only
check. Snapshot creation/audit persistence were exercised through authenticated
fixture API/database tests. This is not a new personal-browser snapshot test.

Real qwen2.5-coder:3b used the production LangGraph and validators against the
saved two-file snapshot and a harmless arithmetic fixture. First exact two-file
explanation: 85.06s, rejected with AUTOMATION_CITATION_INVALID because main.py
lacked citations; no suggestion saved. After making per-file choices explicit,
one manual repeat reached the 90.03s inference deadline and returned AI_TIMEOUT.
There is no automatic retry, fake citation attachment or deadline bypass.

Real patch generation: 40.84s, validated, main.py evidence, MEDIUM confidence.
The unified diff changes `return a - b` to `return a + b`; the model omitted the
final newline and the backend correctly included the unified-diff no-newline
marker. No unrelated files changed. The model described arithmetic correctness
as a "Security risk", illustrating that its interpretation still needs human
review. The backend explicitly labeled it an unverified hypothesis. The patch
was never applied and no suggested validation was executed. This graph-only
live check did not persist a personal proposal; database review persistence was
verified separately with controlled upstream responses.

## Review, security and UI verification

Backend tests use PostgreSQL, mocked GitHub/Ollama and existing auth controls.
They cover authentication, origin/CSRF, live refresh-session ownership binding,
repository authorization, exact revision/blob integrity, path/file budgets,
credential rejection and Python configuration false positives, control characters,
invented/duplicate/wrong-range citations, malformed model output, prompt-injection
boundaries, protected paths, replacement/diff validation and before-content hashes.
They also cover proposal idempotency, GET reload, hash tampering, approval/rejection/
cancellation, expiry, replay, cross-user isolation, concurrent approval, rollback,
audit records and disabled execution. New regressions cover multi-file coverage,
confidence/risk treatment and decision history after proposal expiry.

The automation implementation has no subprocess, shell, eval or patch-application
path. The execute endpoint always audits a denial and returns 503. Model output
cannot add tools or commands; validation choices are typed allowlisted metadata.
Per-user PostgreSQL advisory locks and proposal row locks serialize decisions;
limits remain six mutations/minute, ten active snapshots and five proposals/session.
No CI job requires real GitHub credentials, Ollama, GPU, microphone or voice models.
Existing auth/refresh/RBAC/GitHub/voice suites passed. This does not prove fresh
microphone or Piper hardware acceptance; no microphone/Piper behavior was changed.

`$env:CODEMATE_E2E='1'; node scripts/verify-automation-browser.mjs`
passed using actual Microsoft Edge, FastAPI, the isolated production Next.js
build and the guarded test database, with controlled GitHub/Ollama upstreams.
Assertions cover snapshot creation, source explanation, Reload session with only
one generation POST, exact diff display, rejection, confirmation-dialog approval,
cancellation, persisted decisions after refresh, secret-path rejection and voice
navigation. Desktop and 390px mobile screenshots were inspected. Output reports
executionRequests=0, mobileOverflow=false and pageErrors=0. Disposable accounts
and this script's servers were cleaned up.

The first extended browser attempt correctly hit the existing mutation limit
before cancellation. The final run waits for the next rate window, preserving
production limits, then passes. This is controlled E2E acceptance rather than a
personal authenticated browser retest or real-model browser inference.

A configured-secret literal scan across changed/untracked candidate files found
no configured JWT, GitHub client-secret or encryption-key literals. Only .env
example files are tracked; no model weights, personal source snapshots or private
data were added. This is a targeted review, not a formal penetration test.

## Exact proposed staging allowlist (updated for blocker fixes)

Nothing has been staged. Review this allowlist before authorizing staging. It
includes the pre-existing Milestone 7 implementation as well as this follow-up.
Exclude frontend/next-env.d.ts, PostCSS stash content, .env files, generated build
outputs, browser screenshots and verification logs.

```text
README.md
backend/alembic/versions/0005_safe_automation.py
backend/app/api/routes/automation.py
backend/app/automation/__init__.py
backend/app/automation/citations.py
backend/app/automation/graph.py
backend/app/automation/explanations.py
backend/app/automation/observations.py
backend/app/automation/policy.py
backend/app/automation/schemas.py
backend/app/automation/source_scan.py
backend/app/integrations/github/logs.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/automation.py
backend/app/services/automation_service.py
backend/app/voice/agent.py
backend/app/voice/schemas.py
backend/tests/test_automation.py
backend/tests/test_automation_explanations.py
backend/tests/test_database.py
docs/ARCHITECTURE.md
docs/MILESTONE_7_FINAL_VERIFICATION.md
docs/PROGRESS.md
docs/WINDOWS.md
frontend/next.config.ts
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
frontend/src/tests/api.test.ts
frontend/src/tests/automation.test.tsx
frontend/src/tests/build-config.test.ts
```

Recommended commit message:
`feat: add secure developer automation proposals for Milestone 7`

## Remaining steps recorded before this blocker follow-up (historical)

1. Obtain a successful real two-file explanation with relevant citations and
   independently inspect factual claims, including framework settings behavior.
2. Complete personal authenticated browser acceptance for a newly created real
   snapshot, explanation, Reload session, harmless proposal and review decisions.
3. Resolve or explicitly accept the default .next cache build issue; the isolated
   production build already passes. Preserve generated files when troubleshooting.
4. Review the known five high development-tooling advisories and bounded session
   retention. Execution remains disabled regardless of review approval.
5. Review the complete diff and allowlist, then request explicit staging/commit/
   push approval. Do not merge automatically. No Milestone 8 work is authorized.
