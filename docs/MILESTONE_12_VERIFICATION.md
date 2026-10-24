# Milestone 12 final integration and portfolio verification

Date: 2026-10-24. Scope: local portfolio release with explicit limitations.
Recommendation: B, local demonstration ready with limitations. Public production readiness is not certified. Sandbox
execution remains disabled. This report supersedes the initial dependency stop.

## A. Implementation and initial audit

Confirmed clean main at ec5c9b1269456c71da34799bb108e63dc4bf8eed and four preserved
stashes before creating feature/milestone-12-final-release. Reviewed existing
README, architecture, deployment, Windows/progress and milestone evidence, API
startup/security, auth, GitHub/AI/voice, preview policy, models/migrations, browser
fixtures and read-only CI. Historical counts 562/175 were not treated as current.

The first fresh npm audit found affected production Zod and development Undici,
so implementation stopped and the initial audit/matrix was recorded. The user
explicitly approved focused remediation and continuation. No incompatible forced
fix, ignored failure, execution bypass or new major subsystem was introduced.

Implemented patched dependencies, explicit response/schema resource limits,
controlled acceptance gaps, exact fixture cleanup, bounded browser waits, responsive
review readability, keyboard-scrollable validation commands, current landing and
dashboard copy, concise README and professional demo/release/case-study material.

## B. Complete journey inventory and acceptance matrix

Coverage paths refer to backend/tests, frontend/src/tests, frontend/e2e or
frontend/scripts. The gap column preserves the initial audit plan; actual outcomes
are in the last column and sections C-G. Live-service/hardware omissions remain
explicit rather than being counted as passing automated evidence.

| Feature and entry | Prerequisite | Expected behavior / failure behavior | Existing coverage | Gap or remaining verification | M12 result |
| --- | --- | --- | --- | --- | --- |
| Register/login, /register and /login | Guarded DB | Validated account/session; invalid/duplicate/rate-limited requests rejected | test_auth.py, forms.test.tsx, workspace.spec.ts | Rerun complete browser journey | Existing regressions and applicable controlled browser checks passed |
| Refresh/logout/expired session, auth endpoints | Disposable cookie session | Rotation/revocation; replay/CSRF/expired denial, honest local-only logout on outage | test_refresh.py, session.test.ts, provider.test.tsx, workspace.spec.ts | Add expired-cookie browser scenario if absent | Existing regressions and applicable controlled browser checks passed |
| Protected dashboard/profile/settings | Active account | Hide content until verified; safe account fields/preferences; anonymous denial | test_rbac.py, dashboard.test.tsx, workspace.spec.ts | Rerun responsive navigation | Existing regressions and applicable controlled browser checks passed |
| Admin directory/metrics | Disposable ADMIN | Read-only access; USER/anonymous denied, aggregate metrics without identity labels | test_rbac.py, test_operations.py, workspace.spec.ts | Browser metrics authorization journey | Existing regressions and applicable controlled browser checks passed |
| GitHub App connect/revocation | Authorized controlled installation | PKCE/state/encrypted backend credential; denied/revoked access fails closed | test_github.py, github.test.tsx, workspace.spec.ts | Rerun; separate narrow real GitHub acceptance | Controlled acceptance passed; live personal GitHub not tested |
| Repositories/contents/PRs/issues | Authorized repository | Bounded read-only views; missing/private/rate-limited data handled safely | test_github.py, workspace.spec.ts | Rerun controlled exploration and pinned evidence | Existing regressions and applicable controlled browser checks passed |
| Actions/jobs/failure logs | Controlled failed run | Bounded redacted inert logs; inaccessible/rate-limited cases explicit | test_github.py, workspace.spec.ts | Rerun complete failure-to-diagnosis flow | Existing regressions and applicable controlled browser checks passed |
| Ollama/LangGraph diagnosis | Controlled failure and worker | Grounded report; invalid output/timeouts/cancellation bounded | test_ai.py, ai.test.tsx, workspace.spec.ts | Separate live model availability/inference check | Controlled browser/backend passed; real Ollama report passed |
| Pinned source explanation/citations | Authorized snapshot | Valid source citations; fabricated/invalid evidence rejected | test_automation_explanations.py, test_automation_targeted.py, automation.test.tsx | Rerun explanation and reload browser journey | Existing regressions and applicable controlled browser checks passed |
| Patch generation/exact review | Snapshot and explicit request | Backend-generated diff; unsupported/path/secret edits rejected | test_automation.py, test_automation_targeted.py, automation.test.tsx | Rerun controlled proposal flow | Existing regressions and applicable controlled browser checks passed |
| Approve/reject/cancel/history/idempotency | Owned proposal | Explicit decisions persist; expiry/replay/cross-user denial | test_automation.py, automation.test.tsx, verify-automation-browser.mjs | Confirm all decisions and refresh restoration in browser | Existing regressions and applicable controlled browser checks passed |
| Exact sandbox preview/hashes | Reviewed approved proposal | Pinned hashes/audit, six blockers; stale/tampered confirmation denied | test_sandbox.py, sandbox.test.tsx, verify-automation-browser.mjs | Rerun backend and browser gate checks | Existing regressions and applicable controlled browser checks passed |
| Preview cancel/reload and disabled Run | Owned preview | Durable cancellation/history; SANDBOX_UNVERIFIED, no execution | test_sandbox.py, sandbox.test.tsx, verify-automation-browser.mjs | Verify zero execution requests again | Existing regressions and applicable controlled browser checks passed |
| Record/transcribe/safe commands/TTS | Fixture audio or optional local models | Bounded speech and authorized navigation; missing devices/permission/model errors explicit | test_voice.py, voice.test.tsx, verify_voice_local.py | Fixture browser audio, optional real pipeline/manual hardware | Backend/frontend fixtures and real synthetic speech passed; hardware not tested |
| Health/readiness/DB recovery | Guarded DB | Liveness separate; sanitized readiness failure/recovery | test_health.py, test_operations.py, test_database.py | Rerun current migration and outage regressions | Existing regressions and applicable controlled browser checks passed |
| JSON logs/correlation/private metrics | Trusted application | Validated IDs/templates/aggregates; no raw secrets, ADMIN restriction | test_operations.py, api.test.ts | Rerun concurrent/privacy regressions | Existing regressions and applicable controlled browser checks passed |
| Mobile/tablet/keyboard/dialogs | Production frontend | Focus/labeled controls, readable diff/logs; no overflow or false availability | workspace.spec.ts, automation/sandbox component tests | Review 390/768/desktop, zoom/contrast/manual limits | Existing regressions and applicable controlled browser checks passed |

## C. Tests, static checks and execution gate

- Initial full backend run: 562 passed in 257.55 seconds, warnings as errors.
- Final post-filelock full backend regression: 562 passed in 243.69 seconds with warnings as errors (after filelock 4.2.1).
- Frontend: 181 passed across 12 files; six new resource-limit cases. Existing
  dashboard test updated to assert the real diagnostics link and disabled execution.
- ESLint with zero warning budget and TypeScript: passed after final source edits.
- Production Next.js 16.4.2 build: passed. Final measured build: 12.18 seconds locally (normal production build; a subsequent normal rebuild also passed).
- Ruff lint and format, including the modified E2E Python helper: passed.
- pip check: passed. Alembic heads/current: 0006_sandbox_previews; check found no
  new upgrade operations. No schema migration or execution queue was added.
- Controlled benchmark: one opt-in case passed in 4.98 seconds, separate from suite.
- Live pinned-source opt-in regression: one passed in 17.19 seconds; separate from
  deterministic suite totals and never a CI prerequisite.
- No backend/frontend warning suppression or security-test removal.

Backend regression includes cross-user ownership, RBAC, CSRF, secure production
cookies, refresh replay/expiry/concurrency, evidence/source/citation validation,
unsafe model output, tampered/expired approvals, exact hashes, preview cancellation
and valid confirmation denied with SANDBOX_UNVERIFIED. API/schema capability flags
remain literal false, applied false, validation not_executed. Frontend Run is
literally disabled; voice cannot authorize execution. Six requirements remain
worker identity, launcher separation, approved provenance, dedicated isolation,
durable recovery and approved patch integration. No flag or environment override.

GitHub client/permissions, launcher/host command surface and trusted analysis-worker
boundaries were not broadened. No GitHub write permission, repository applier,
Docker-control endpoint, socket/host mount, privileged job or automatic deployment.

## D. Current dependency findings and compatibility review

Vendor advisories and installed/locked paths were checked on 2026-10-24.

| Dependency | Before | After | Path and justification |
| --- | --- | --- | --- |
| zod | 3.25.76 | 4.6.6 exact | Direct runtime dependency; deduped resolver/react-hooks/zod-validation-error consumers |
| undici | 8.11.2 | 8.12.2 exact scoped override | jsdom 30.1.2 development dependency, existing range ^8.11.2 permits this fix |
| filelock | 4.1.2 | 4.2.1 exact lock, >=4.2.1,<5 runtime floor | huggingface_hub 2.2.0 requires >=3.10.0; compatible security update found by fresh Python audit |

npm lock comparison changed only the root Zod declaration and those two package
entries. Next.js/eslint-config-next remain 16.4.2; unrelated npm pins unchanged.
No new direct Undici dependency or forced major update. Python installed update
used --no-deps and changed only filelock; pip check passes. No other Python pin
changed. Normal locked installs retain the same packages with the patched versions.

### Exact advisories

- Zod GHSA-mrhx-c7xc-m3w5, CVE-2023-54404: affected <4.6.6, patched 4.6.6. Memory
  exhaustion from excessive collection-validation issues. The original installed
  3.25.76 was affected. [Reviewed advisory](https://github.com/advisories/GHSA-mrhx-c7xc-m3w5).
- Undici GHSA-4qv8-2p9j-2685, CVE-2026-109924: EventSource retained-state exhaustion,
  moderate; affected 8.0.0 through 8.12.1, patched 8.12.2.
- Undici GHSA-f72v-6w45-q472, CVE-2026-109841: mixed-case integrity-token bypass,
  moderate; affected 8.0.0 through 8.12.1, patched 8.12.2.
- Undici GHSA-xjj6-f33q-929c, CVE-2026-109869: unhandled error with excessive
  content-encodings, high; affected 8.0.0 through 8.12.1, patched 8.12.2.
  Original 8.11.2 was affected by all three. Other major release ranges are not
  relevant to this installed path. [Undici high advisory](https://github.com/advisories/GHSA-xjj6-f33q-929c),
  [EventSource](https://github.com/advisories/GHSA-4qv8-2p9j-2685),
  [integrity](https://github.com/advisories/GHSA-f72v-6w45-q472).
- Fresh Python audit found six filelock IDs: CVE-2026-112906, CVE-2026-112940,
  CVE-2026-112914, CVE-2026-112913, CVE-2026-112937 and CVE-2026-112907. All listed
  fix 4.2.1. The high ReadWriteLock advisory affects >=3.20.4 through 4.2.0 and
  depends on local POSIX writable-directory/SQLite conditions; no application
  call to that lock API or remote exploitation was established. Do not confuse
  package applicability with demonstrated application exploitation.
  [Vendor advisory](https://github.com/tox-dev/filelock/security/advisories/GHSA-v4x8-3wr5-3wq8),
  [vendor 4.2.1 release](https://github.com/tox-dev/filelock/releases/tag/4.2.1).

### Migration and independent resource controls

Zod 4 requires explicit record key/value schemas; migrated all affected records.
Existing error handling uses safeParse results, not removed ZodError.errors.
Form resolvers, transformed email input/output, refined confirmations, strict
readiness uniqueness and generic response types pass tests and TypeScript.
[Vendor migration guide](https://zod.dev/v4/changelog).

Before JSON.parse, decoded response bytes are limited to 4 MiB by streaming reads;
declared length is only an early check. The reader cancels on overflow. Error
responses share the bound; unused generic error bodies are cancelled. Only the
existing speech endpoint can return WAV and audio is limited to 16 MiB. The
request's existing AbortController deadlines remain active during reads.

An iterative pre-schema guard caps arrays at 1000 elements, object keys at 512,
key lengths at 1024, depth at 32, total visited nodes at 20000 and strings at
262144 characters. Schema arrays add max 100 or tighter existing length/max
constraints; schema strings are explicitly bounded, with narrower auth email,
username/password and confirmation limits. This bounds unknown nested fields
before Zod error traversal; the dependency patch is not the only defense.

Six new tests cover streamed/declared/exact byte boundaries and cancellation,
array/record/key/string/depth/node limits, rejection before safeParse, bounded
success/error paths and page/form bounds. No giant resource-exhaustion payload or
hostile execution was needed. These are finite application budgets, not proof
against all resource exhaustion or downstream system-wide limits.

### Fresh audit outcomes

npm production audit: zero vulnerabilities, exit 0. npm full audit: zero
vulnerabilities, exit 0. Isolated pip-audit against all 85 lockfile pins: no known
vulnerabilities after filelock, exit 0. pip check passes. Missing full artifact
hashes remain a lockfile limitation; no warning was suppressed. The initial audit
invocation omitted --no-deps and was rejected; the corrected all-pins audit ran
successfully. Historical five development-tooling advisories did not reappear in
current registry results. Historical clean audits were not assumed current.

## E. Controlled desktop, tablet, mobile and accessibility

Existing production-build Edge suite extended: eight scenarios passed in the final rerun in 21.1s,
including registration/login, reload/rotation, profile/settings, revoked logout,
anonymous protection, mobile keyboard dialog focus/Escape, cross-tab invalidation,
ADMIN directory/metrics and USER/anonymous metrics denial, outage recovery,
controlled GitHub/Actions/diagnosis and missing-refresh-cookie restoration denial.
Actual expired-token/session logic is covered by backend/frontend regressions;
the added browser scenario clears its own cookie, not the clock or backend policy.

The first run found an ambiguous existing model-unavailable locator matching two
legitimate messages. It was made exact and the entire suite passed; no assertion
or backend validation was removed. An initial sandboxed Vitest run failed due to
inaccessible temporary transformed-module files. Unsandboxed reruns passed; this
was not a dependency compatibility waiver.

The controlled automation demo passed at desktop, 768-pixel tablet and 390-pixel
mobile. It verified source inspection/explanation, exact diff, rejection, review
approval, preparation/cancellation/history, safe voice navigation and secret-path
denial. Six blockers visible; zero execution requests, page errors or overflow.
Keyboard focus on preparation control asserted. Screenshot regions reviewed.
Final rerun passed all eight scenarios in 21.1 seconds, then the normal production
build and responsive automation demo passed. Dashboard timing is in section H.
Desktop/mobile element screenshots contain the sticky navigation overlay in some
positions; screenshots stay diagnostic/ignored, not a formal accessibility record.

Review styling preserves the design, improves wrapping/line height and keyboard
scrolling, keeps focus visible and disabled controls unavailable. Stale landing,
overview and footer milestone claims were replaced with accurate feature/status
copy. No fabricated progress. Existing reduced-motion behavior, semantic forms,
native dialogs and names remain. Selected palette contrast ratios: dark muted
7.36, light muted 6.01, dark accent 10.89, light accent 5.66 against their surface.
These spot checks are not comprehensive contrast/WCAG certification. Screen-reader
hardware, all zoom/text scales, every color pair and formal assistive-tech audit
remain manual limitations. Metrics are an ADMIN API, not a new public dashboard.

The E2E helper no longer deletes all test throttle rows during prepare. Cleanup
uses exact known account identities and their account throttle hashes; shared IP
buckets are retained. Occupied ports are refused. Browser waits are finite.
No personal database, installation, volume or unrelated process is cleaned.

## F. Real integrations and claim boundaries

Real Ollama /api/tags responded and confirmed installed qwen2.5-coder:3b, without
a model download. Existing verify_local_ai.py used real inference, controlled
GitHub failure evidence and an owned guarded-DB account: completed in 15.8 seconds,
two findings, two evidence entries, complete evidence, schema valid and persisted
then reloaded. This is one live inference sample, not a latency distribution.
Citation validation passed. Separately, the existing local_docstring.py opt-in
source test passed: one real model call, 14.34-second proposal/review/preview flow,
controlled pinned main.py source, docstring-only AST preservation, persisted reload
and idempotent retry, exact preview binding and applied false. The whole opt-in
test took 17.19 seconds. The AST check is a trusted test assertion, not repository
code execution or sandbox validation. No repository source file was modified.
A manual factual review of every investigation-report model statement was
not recorded, so schema validity is not claimed as proof of model truth or repair
quality. Timeout/invalid-model failure handling passed deterministic regression.

Real GitHub: not run. No unattended authenticated browser session or explicitly
selected live repository was supplied for this acceptance. Controlled GitHub token
exchange, installation authorization, pinned evidence, Actions, rate limits and
revoked-access denial are tested; this is not fresh personal-account acceptance.
DEMO_GUIDE.md gives the optional narrowly read-only manual procedure. No personal
access was revoked, repository mutated or token exposed for the demonstration.

## G. Voice

Backend/frontend fixture tests cover audio decoding limits, unsupported commands,
authorization, confirmation, cancellation, idempotency and missing-model/device
feedback. Typed browser voice navigation passed. Optional existing local speech
models were present. verify_voice_local.py generated 131116 WAV bytes via Piper,
transcribed "Code Mate, Open My GitHub Repositories." with whisper, language en,
and real Ollama interpreted a paraphrase as safe navigation to profile. Synthetic
input only; no microphone recording, speaker playback or hardware acceptance.
The generated WAV stays ignored. No additional models downloaded. Hardware/device
permission and example-command steps are provided in DEMO_GUIDE.md; unavailable or
ambiguous commands must remain safe. Voice never authorizes sandbox execution.

## H. Performance and stability

Comparable API benchmark: Windows, Python 3.12.10, in-process TestClient, real
guarded PostgreSQL, controlled GitHub/model fixtures, 32-byte source, one warmup
and 20 samples per GET. Nearest-rank p95. M11 hardened artifact preserved.

| Operation | M11 median/p95 ms | M12 median/p95 ms | Samples each |
| --- | --- | --- | --- |
| Health | 4.859 / 6.166 | 4.076 / 4.523 | 20 |
| Authenticated account | 14.018 / 15.616 | 14.570 / 17.189 | 20 |
| GitHub fixture listing | 22.920 / 24.496 | 26.121 / 42.839 | 20 |
| Proposal/session history | 17.351 / 18.408 | 16.864 / 18.281 | 20 |
| Preview read | 31.535 / 32.702 | 29.815 / 33.452 | 20 |

All recorded requests succeeded; any non-200 fails the benchmark. Controlled AI
explanation: final M11 96.795 ms; M12 116.098 ms, one sample each, no p95. Python tracemalloc
peak M11 572171 bytes versus M12 572966, not total process RSS. Input/transport and
upstreams are explicitly recorded in docs/milestone-12-benchmark.json.

Some metrics regress. Small local samples and scheduling noise do not establish
causal changes, load capacity or percentage improvements. No security check was
weakened. No uncontrolled load against GitHub or Ollama. Dashboard navigation to the verified account heading in Edge: five warmed samples,
median 232.150 ms and nearest-rank p95 324.454 ms, zero errors. This includes normal
page navigation/session restoration on localhost with controlled upstreams. There
is no comparable M11 browser dashboard sample, so no speedup is claimed. Final
normal build took 12.18 seconds versus M11 24.72 seconds; build cache/load varies
and single build samples cannot establish a causal improvement.

## I. Deployment and CI readiness

The existing bounded loopback startup, explicit production secrets/CORS/cookies,
private database/model services, shutdown and readiness foundation remain. The
controlled helper ran real Next/FastAPI/guarded PostgreSQL and stopped owned child
servers. No public deployment or hosting purchase. TLS/ingress trust, backups and
restore drills, operational retention/alerts, resource sizing and public security
review remain unverified production requirements. PostgreSQL volume preserved.

Existing GitHub Actions inspected: contents read, pinned actions, no persisted
checkout credential, locked/cached installs, real isolated PostgreSQL, backend
warnings-as-errors/lint/format/migrations and frontend tests/static/build. No
personal GitHub/Ollama/microphone/GPU or privileged sandbox job is required.
No automatic deploy or workflow secret exposure added. Hosted Actions was not
triggered; local checks are not a hosted CI completion claim.

## J-L. Portfolio material and handoff

- README.md: problem, capabilities, stack/diagram, setup, demo, tests/security,
  limitations and future work, replacing historical overview clutter.
- docs/DEMO_GUIDE.md: reproducible controlled commands, ten-minute failure-to-review
  narrative, fixture labels, real-service/hardware steps and presentation privacy.
- docs/PROJECT_OVERVIEW.md: Mermaid architecture, technical case study, decisions,
  tradeoffs/challenges/lessons, thirty-second/two-minute explanations, architecture,
  auth/AI/GitHub/review/threat-model interview notes and three grounded resume bullets.
- docs/RELEASE_CHECKLIST.md: evidence-based checks, fail-closed permissions/execution,
  deployment distinction and explicit approval before staging/release actions.
- Architecture, Windows and progress docs updated with final-release boundaries.

No customer adoption, autonomous repair, public production use, execution success
or unsupported performance improvement is invented. Future isolation work is not
presented as deployed functionality or an additional implemented milestone.

## M. Remaining limitations and release recommendation

Recommendation B: local demonstration ready with limitations after passing local
checks. Real GitHub and physical hardware acceptance remain unverified. Real model
schema/citation success is not an independent truth/repair assessment. Public TLS,
backups, strict nonce CSP, distributed telemetry, formal accessibility/security
review and load sizing remain separate work. Stateless access tokens retain their
configured lifetime after logout; refresh revocation is immediate. Missing full
Python wheel hashes remain documented. All six runner requirements are unmet;
no isolated patch execution is claimed. No unresolved dependency compatibility
failure or known advisory remains in the final audits, subject to point-in-time
registry coverage rather than a guarantee of security.

## N-O. Exact changed-file list and future staging allowlist

The exact 34 intended changed paths, expanded and reviewed:

```text
README.md
backend/requirements-dev.lock.txt
backend/requirements.txt
backend/tests/benchmark_demo.py
docs/ARCHITECTURE.md
docs/DEMO_GUIDE.md
docs/MILESTONE_12_VERIFICATION.md
docs/PROGRESS.md
docs/PROJECT_OVERVIEW.md
docs/RELEASE_CHECKLIST.md
docs/WINDOWS.md
docs/milestone-12-benchmark.json
docs/milestone-12-browser-benchmark.json
frontend/e2e/workspace.spec.ts
frontend/package-lock.json
frontend/package.json
frontend/scripts/e2e_backend.py
frontend/scripts/verify-automation-browser.mjs
frontend/src/app/globals.css
frontend/src/app/page.tsx
frontend/src/components/automation/sandbox-panel.tsx
frontend/src/components/dashboard/dashboard-shell.tsx
frontend/src/components/dashboard/overview.tsx
frontend/src/lib/ai.ts
frontend/src/lib/api/client.ts
frontend/src/lib/api/limits.ts
frontend/src/lib/auth/validation.ts
frontend/src/lib/automation.ts
frontend/src/lib/github.ts
frontend/src/lib/sandbox.ts
frontend/src/lib/voice.ts
frontend/src/tests/dashboard.test.tsx
frontend/src/tests/limits.test.ts
frontend/src/types/api.ts
```

This list authorizes review only, not staging. Populated environments, models,
synthetic WAV, screenshots, logs, .next/.next-e2e, caches and generated declarations
are excluded. No files are staged, committed, pushed, merged, reset or deleted.

## P. Git preservation

Branch feature/milestone-12-final-release. HEAD remains
ec5c9b1269456c71da34799bb108e63dc4bf8eed. Four preserved stash hashes:

```text
3fce76236a951bc34c86aea3c2ec42a651677fd9
3ddb4687fae40b8a95cceb0b0f5666d21ba954ac
e38d863d98bab479bb87e0978764f9fcc2c1c18c
26b23eadaed05d3865e308f4dc9e45e4441156e1
```

Final git diff --check passed. Expanded inventory matches the 34-path allowlist.
Index empty; next-env.d.ts has no diff and no frontend/AGENTS.md was generated.
Credential-signature and populated local-secret-value scans found no matches.
New docs contain no em dash characters. Four stash IDs match the starting list.
Generated audio/screenshots/logs/builds remain ignored. No unexpected source edits.
No deployment or additional milestone begun.
