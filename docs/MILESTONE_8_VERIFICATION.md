# Milestone 8 threat model and verification

Status: safe preparation fallback. Execution is disabled in code. Docker Desktop's
Linux engine was initially unavailable on 2026-10-19, including an elevated
read-only probe. Starting the installed Desktop service restored it. The dedicated
CodeMate PostgreSQL container then reported healthy. Engine 29.6.2 reports Linux
x86_64, built-in seccomp and cgroup namespaces. Read-only inspection found existing
Python/Node images, but no image or isolated launcher was selected or approved.
A Docker container alone is not evidence of a secure sandbox.

## Threats and boundaries

| Threat | Current mitigation | Required before execution |
| --- | --- | --- |
| Malicious repository code, dependencies and install scripts | No repository code or installation is executed | Separate restricted worker and audited offline image |
| Container escape and privilege escalation | No runtime launcher exists | Stronger VM/service isolation, syscall and privilege negative tests |
| Host filesystem modification, symlinks, junctions and hard links | No source workspace is materialized; M7 regular blob/path policy reused | Race-resistant materialization and real host containment tests |
| Network exfiltration and host service access | No validation runs | Real no-egress and host-service isolation tests |
| Docker socket abuse | API has no runtime-management integration | Separate constrained launcher identity; no runtime socket in sandbox |
| Credential theft | No tokens, secrets or application environment sent to execution | Credential-free source handoff and negative secret-read tests |
| Denial of service | Bounded preview size/count; short expiry | Verified CPU, memory, PID, disk, output and wall-time limits |
| Malicious Git content or diffs | Pinned M7 snapshots; regenerate patch from validated replacements and compare all artifacts | Full tree/commit integrity and post-apply manifest checks |
| Approval race and replay | Owner serialization, unique request ID, immutable preview binding, no execution authorization accepted | Atomic worker claim and single-use short-lived confirmation |
| Cross-user access | Owner queries plus existing GitHub authorization and CSRF/session checks | Worker ownership and service boundary tests |
| Prompt injection and untrusted output | No model command authority; no execution output invented; React text rendering | Bounded redacted logs and real result provenance |

The authenticated API, database, GitHub fetcher, model, repository, execution
worker and runtime are separate trust domains. Worker/runtime domains are designed
only in this fallback. The API must never become a Docker launcher or execute
repository commands. Container escape resistance remains unverified and may need
a dedicated VM or stronger sandbox service beyond ordinary Docker Desktop.

## Gate and delivery scope

Preparation records awaiting confirmation, cancelled or expired previews. Review
approval never authorizes execution. A confirmation endpoint checks ownership,
expiry, repository permission and immutable binding, audits denial, and always
returns SANDBOX_UNVERIFIED. There is no environment-variable override. No queue,
worker, physical workspace, image, image digest, exit code or test output is claimed.
The durable UUID is a preview identity, not a materialized workspace.

The initial candidate profile is python_syntax, with fixed python -I -S arguments
and a future trusted AST-only validator. It is a preview contract, not a runnable
host command. Pytest, package scripts, npm/pip installation and networking are not
supported. A future implementation must validate the trusted validator and image.

Designed isolation contract: digest-pinned audited offline image, UID/GID 65532,
read-only root, no new privileges, all capabilities dropped, private namespaces,
no network, no mounts of host paths/devices/socket/secrets, bounded tmpfs, 64 PIDs,
256 MiB memory, one CPU, 30 seconds and 64 KiB combined output. Seccomp and stronger
isolation must be verified. None of these controls has been verified with Docker.

Before replacing the hard denial: verify image provenance/digest, worker separation,
full source integrity, disposable patch materialization, exact changed-file hashes,
no host access or egress, resource exhaustion controls, timeout/cancel cleanup,
lease/crash recovery and real exit-code/log capture in an opt-in isolated suite.
Never run repository fixtures on the host or an excessively privileged CI runner.

## A. Implementation summary

Milestone 8 safe preparation fallback is implemented on
feature/milestone-8-secure-sandbox, based on clean main 8e6aff4. The existing
Developer Automation dashboard now supports exact, durable execution previews,
fixed Python syntax profile selection, cancellation, restoration and audit history.
Review approval is separate from execution confirmation. Confirmation always
fails closed. Milestone 9 has not started.

## B. Architecture and threat model

See the threat table above and ARCHITECTURE.md. PostgreSQL is the durable boundary
for preparation. The existing authenticated API handles trusted metadata only.
The model has no execution tools. Worker/runtime separation, credential-free source
handoff and the hardened sandbox are prerequisites, not implemented runtime claims.

## C. File changes

New backend modules implement the gate/policy, strict request/response contracts,
preview persistence and audited service/routes. Existing app registration, model
exports, readiness revision and test head expectations include the additive schema.
Voice phrases navigate to the existing dashboard. Frontend schemas reject fabricated
applied/output/success fields, and the panel displays exact previews and disabled
Run controls. Authentication session routing and structured error handling include
the sandbox API. The browser script extends existing M7 regression coverage.
Documentation and regression suites are updated. The exact file allowlist is below.

## D. Database migrations

0006_sandbox_previews follows 0005_safe_automation with no branch in the revision
graph. It adds sandbox_previews and sandbox_audit, owner/request uniqueness,
owner/time indexing, a strict preparation-state constraint, expiry, immutable
binding data and proposal/audit foreign keys. Existing milestone data is preserved.
The development database was at 0005, upgraded additively to 0006, and Alembic check
reported no new upgrade operations. Test migrations run only under the existing
guarded codemate_test_user/codemate_test_db identity on 127.0.0.1:5433. Migration
roundtrip tests never target the development database.

## E. Sandbox isolation settings

The proposed settings are recorded in each preview and described above. They are
not applied to a runtime. No image digest is approved. The Docker inventory includes
existing digest-addressed Python and Node images, but provenance and a trusted
validator image have not been verified. Built-in seccomp/cgroup namespace support
does not prove no-egress, host isolation or escape resistance. No sandbox or Docker
socket is created or mounted by the API.

## F. Security tests and actual results

Preparation tests cover authentication, CSRF/Origin/custom-header denial, cross-user
history/detail/cancel denial, expired or rejected proposals, hash/source/approval
mismatch, rehashed malicious paths and artifacts, fixed profile enforcement,
request idempotency, concurrent preparation, final cancellation, expiry, voice
rejection and fail-closed valid confirmation. Repeated valid confirmation produces
503 and no queued state; its denial event is deduplicated. Existing M7 authorization,
Git blob/path, symlink/executable, citation and prompt-injection regressions remain.
UI tests cover inert malicious diff text, disabled Run, duplicate clicks, lost
response request-ID reuse, parent-loading races and persisted history reads.

Real network, host filesystem, Docker socket, privilege escalation, resource limits,
workspace cleanup, running-job timeout/cancellation, worker crash/lease recovery
and output redaction in a running sandbox are NOT integration-tested. No malicious
repository code was executed on the host. No simulated test is counted as proof
of container isolation. No execution output is synthesized by AI.

## G. Automated verification

Backend: 448 passed in 202.29 seconds with warnings as errors. This includes
all 394 existing tests, 24 new PostgreSQL/API tests and 30 independent security/voice
cases. Full migration downgrade/upgrade and metadata consistency tests passed in
the guarded test database. The final browser outcome is recorded below.
Frontend: 167 tests passed across 11 files. ESLint with zero warnings, TypeScript
and Next.js 16.4.0 production build passed. Ruff lint and formatting passed for
109 Python files. pip check passed. Alembic history/offline SQL generation and
live development head/schema checks passed. npm production audit reports zero
vulnerabilities; full npm audit reports the same five high development-tooling
findings through the existing ESLint/fast-glob/micromatch/braces chain. Dependencies
and lockfiles were not changed. A raw full-audit exit of 1 reflects those findings.

Sandboxed Vitest initially failed to read temporary worker files, and sandboxed
Next.js could not start its CSS worker. Elevated reruns passed. Backend database
access required execution outside the tool sandbox. One new concurrency assertion
was corrected to match existing VOICE_BUSY/409 behavior; a retry still returns the
same one preview. No pre-existing tests were weakened. CI workflow permissions
remain contents:read, with no new Docker/socket/model requirement. Remote CI was
not run because there was no push. A changed-file scan found no matches to actual
local credential values. Environment files, keys and model/audio artifacts were
not changed or staged.

## H. Real patch and validation verification

Not performed. No physical repository materialization, patch application, validation
execution or actual exit-code/output report is available. Real FastAPI/PostgreSQL
preparation uses controlled GitHub/Ollama fixtures; those are not personal GitHub
or real-model repair validation. The user's checkout is not a target workspace.
The preview expected_manifest contains predicted after-hashes computed from exact
approved replacements; actual changed_manifest remains empty.

## I. Windows setup and startup

See docs/WINDOWS.md, Milestone 8 preparation fallback, for exact PowerShell commands
for existing Docker/PostgreSQL, additive migration, FastAPI, existing AI worker,
Ollama readiness, Next.js, unit/lint/build checks and manual preview verification.
No execution-worker startup, image build or safety-gate enable command exists.
Optional browser verification, after a production build and with ports 3000/8001
free and no concurrent backend test suite:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\frontend'
node scripts/verify-automation-browser.mjs
```

The script uses its own headless Edge context, child servers and disposable guarded
test account. It preserves existing personal browsers and unrelated containers.

## J. Known limitations

This is the permitted safe fallback, not a verified runner. It intentionally omits
worker execution/leases, materialization, patch application, real validation,
container lifecycle, logs and generated result summaries. Those require a stronger
verified execution boundary. Only Python patch previews and one inert syntax
profile are supported. A future trusted AST validator must exist inside a verified
image; the displayed path is a proposed contract. No package installs are allowed.
A maximum of 100 previews per account is retained without automatic deletion;
history returns the newest 50. A new request ID is needed for a fresh five-minute
preview after expiry. History requires current GitHub authorization; revocation can
make the account's history request unavailable until permission is restored.

## K. Git status and exact staging allowlist

Nothing is staged, committed, pushed or merged. The three original stashes remain
untouched. No branch or stash was deleted, and no reset/clean was run. Review only
these files for a future explicit staging decision:

```text
README.md
backend/alembic/versions/0006_sandbox_previews.py
backend/app/api/routes/sandbox.py
backend/app/main.py
backend/app/models/__init__.py
backend/app/models/sandbox.py
backend/app/sandbox/__init__.py
backend/app/sandbox/policy.py
backend/app/sandbox/schemas.py
backend/app/services/sandbox_service.py
backend/app/voice/agent.py
backend/pyproject.toml
backend/security_tests/test_sandbox_gate.py
backend/tests/test_database.py
backend/tests/test_sandbox.py
docs/ARCHITECTURE.md
docs/MILESTONE_8_VERIFICATION.md
docs/PROGRESS.md
docs/WINDOWS.md
frontend/scripts/verify-automation-browser.mjs
frontend/src/components/automation/sandbox-panel.tsx
frontend/src/components/automation/workbench.tsx
frontend/src/lib/api/client.ts
frontend/src/lib/auth/session.ts
frontend/src/lib/sandbox.ts
frontend/src/tests/sandbox.test.tsx
```

Screenshots under ignored frontend/test-results are verification artifacts, not
source files to stage. Existing environment configuration remains untouched.

## L. Enablement decision

Execution is DISABLED. The gate is hard-coded and cannot be overridden by settings
or model output. Docker Desktop is available after startup, but image provenance,
worker privilege separation, source materialization and real negative isolation
checks have not established the required safety boundary. Only the preparation
fallback is eligible for review. Do not enable execution to claim completion.

## Final live preparation verification

The extended existing browser script passed against real Next.js production,
FastAPI and the guarded PostgreSQL test database using a disposable Edge context
and controlled GitHub/Ollama responses. It verified source inspection, explanation
reload, exact patch preview, rejection/review approval/cancellation, sandbox preview
creation, disabled separate Run control, cancellation and restored preview history
after navigation/reload, secret-path rejection and voice navigation. It recorded
zero execution/confirmation requests, zero page errors and no horizontal overflow
at 390px width. Desktop and mobile screenshots under frontend/test-results were
visually inspected. Long element captures include sticky navigation overlays;
the actual page overflow assertion passed. No personal browser or GitHub repository
was modified. Only the script's disposable account/child processes were cleaned up.

Final verification: 448 backend tests and 167 frontend tests passed; production
build, Ruff, ESLint, TypeScript, dependency consistency, live Alembic schema checks
and migration roundtrip passed. Production advisory audit is clean; five existing
development-tooling findings remain. Existing authentication/voice/repository
features passed their deterministic regressions. Physical speech, personal GitHub,
real Ollama repair quality and all actual sandbox runtime properties were not
reverified. The disabled fallback is ready for review, with those limits explicit.

## Suggestion-mode follow-up

The single-file generation schema now enforces changes length zero for explain
and one to four for patch mode, while independent backend validation still rejects
noncompliant output. Mode-specific errors direct users to Explain source for an
explanation and to a concrete change request for a patch. No invalid response is
rewritten or silently promoted to another mode. Added four independent regression
cases; 34 independent and 155 automation/explanation tests passed with warnings as
errors, as did targeted Ruff checks. The exact create_app explanation request
passed against real local Ollama and committed main.py in 13.94 seconds with zero
changes/eight validated citations and no persisted proposal. The original rejected
payload/mode could not be established from the screenshot. Semantic claims still
require human review. The running API was restarted and readiness verified.

Add backend/app/automation/graph.py and
backend/security_tests/test_automation_modes.py to the source review allowlist.
Starting the frontend also generated frontend/AGENTS.md and updated
frontend/next-env.d.ts; these development-runtime artifacts are separate from this
fix and were preserved. No changes were staged, committed or pushed.

## Empty-file replacement follow-up

A browser-displayed patch would clear main.py while its prose claimed no improvement
was needed. The mode-specific array-length constraint alone did not exclude this.
The generated replacement schema now requires non-whitespace text, and authoritative
patch validation rejects empty/whitespace-only file contents. Approval regenerates
and checks saved patch artifacts under current policy, so legacy file-clearing
proposals cannot be approved but can still be explicitly rejected. Existing personal
records were not changed. Execution remains disabled.

37 independent security/mode cases and 180 automation/explanation/sandbox tests
passed with warnings as errors; Ruff lint/format passed for 110 files. A real guarded
PostgreSQL fixture verifies legacy valid-hash proposal approval denial and continued
rejection support. The running API was restarted and readiness verified. Nonempty
AI edits still require semantic human review. Additional review-allowlist files:
backend/app/automation/policy.py, backend/app/services/automation_service.py and
backend/tests/test_automation.py, alongside the preceding graph/mode-test changes.

## Exact-path patch generation follow-up

Generation now enumerates exact inspected paths and hashes, caps changes to the
snapshot file count, and supplies complete bounded source for full-file patch
replacements. Explanations retain their existing source contract. Authoritative
backend path/hash/duplicate/citation/secret/empty-file checks remain unchanged;
invalid paths are never remapped. The screenshot did not establish whether the
original rejected response used a wrong path or a duplicate.

41 independent security/mode tests and 180 automation/explanation/sandbox tests
passed with warnings as errors; Ruff lint/format passed for 110 files. The exact
short-docstring request passed with real local Ollama and committed main.py in
58.88 seconds: one exact-path patch, 149 original lines and 160 replacement lines.
An AST comparison after removing the added create_app docstring matched the original
AST, including all imports/executable code. No proposal was saved and no file patch
was applied. Future proposals still require human review. The updated API was
restarted and readiness passed. Follow-up source changes remain in graph.py and
the independent mode tests; no frontend source or environment change was required.

## Final syntax and documentation-operation follow-up

Syntax errors now have a distinct AUTOMATION_PYTHON_SYNTAX_INVALID message instead
of implying that a malformed generated replacement contains credentials. Generic
large-file patches use exact, unique excerpt replacement with no fuzzy matching.
Real generic anchored attempts were rejected: two invalid structured responses
(77.62/80.34s) and a sanitized diagnostic finding an oversized replacement (45.73s).
Those failures remain evidence of limited generic model edit reliability, not
successful repairs. Their raw payloads were not logged or saved.

Explicit add-docstring requests now use a narrower model contract: choose a
backend-issued top-level Python function ID and bounded docstring text. The backend
inserts safely quoted text, preserves other bytes and verifies unchanged executable
AST after excluding the intended docstring. Inline/already-documented targets,
unknown IDs and invalid text fail closed. IDs are not remapped. This operation is
separate from generic patch generation and does not execute repository code.

Two real local Ollama checks of the exact create_app request passed in 9.33s and
7.70s, each adding one line (149 -> 150) with executable AST unchanged. No proposal
was saved and no patch applied. An interim full 470-case suite passed; the final
240-case relevant suite passed, including 58 independent cases and two authenticated
API persistence/review/preview tests. Ruff passed for 115 files. No final full
479-case suite was executed after the documentation-operation addition. Frontend
verification remains historical because no frontend source changed. The updated
API was restarted and readiness passed. Execution remains disabled.

Add these files to the cumulative review allowlist:
backend/app/automation/edits.py, backend/app/automation/docstrings.py,
backend/security_tests/test_targeted_edits.py, backend/security_tests/test_docstrings.py,
backend/tests/test_automation_targeted.py. No files were staged, committed or pushed.

## Exact docstring value comparison correction

Default ast.get_docstring cleans whitespace, causing valid inserted documentation
to fail comparison. The backend now compares the raw value with clean=False while
retaining exact source preservation and executable AST checks. Twelve deterministic
cases reproduced the error before the fix; all 16 new LF/CRLF/whitespace cases now
pass, within the 74 independent security/documentation tests.

The new explicitly opt-in tests/local_docstring.py test passed with real local
Ollama and the authenticated API/guarded test database using controlled GitHub
source at the exact backend/app/main.py path. The actual model returned text whose
cleaned/raw values differed, demonstrating the relevant failure mechanism with a
real response. The final flow passed generation, save/reload, unchanged retry with
one model call, controlled review approval, and preview creation/readback. Its
application flow took 7.19s; total test duration was 9.44s. A prior harness path
assertion was corrected without changing application policy. No patch was applied
or personal proposal changed. Execution remains disabled. The updated API was
restarted; add backend/tests/local_docstring.py to the cumulative review allowlist.

Reproduce only with the existing local Ollama model and no concurrent test DB suite:

```powershell
Set-Location 'D:\shyam\Projects\CodeMate-AI\backend'
$env:CODEMATE_REAL_OLLAMA_DOCSTRING_TEST = '1'
.\.venv\Scripts\python.exe -m pytest tests/local_docstring.py -q -s -W error --tb=line
Remove-Item Env:CODEMATE_REAL_OLLAMA_DOCSTRING_TEST
```

The explicit file name is not discovered by the ordinary test_*.py suite; the flag
prevents accidental inference when that file is selected without opting in.

Final ordinary backend regression run after the raw-docstring correction:
**496 passed in 195.33s**, warnings as errors. Ruff lint passed and formatting
passed for 116 files. The separate opt-in real Ollama/API case passed in addition;
it is not counted in the 496. No existing tests were removed, weakened or disabled.
Frontend source was unchanged. Execution is still disabled and no files were staged,
committed, pushed or merged.
