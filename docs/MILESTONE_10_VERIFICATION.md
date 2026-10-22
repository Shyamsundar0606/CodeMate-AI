# Milestone 10 verification, 2026-10-22

Status: preparation-only admission layers and dependency remediation. Execution
DISABLED. Full restricted-runner completion is not claimed. Fundamental worker,
launcher and hostile-code boundary requirements remain unverified on this machine.

## A. Implementation summary and initial audit

Confirmed clean main at f2b80c3, the expected M9 merge, before creating
feature/milestone-10-restricted-runner. Recorded the same four original stash IDs.
The README, architecture, Windows/progress and M7/M8/M9 verification documents,
M9 threat model/runtime evidence, prototype, authorization, automation/sandbox
services/models/routes, existing AI worker, migrations, tests, Compose and CI
form the reviewed baseline. Migration head is 0006_sandbox_previews.

New non-executing readiness metadata lists six explicit unmet requirements. The
authenticated existing capabilities endpoint has a strict response model. The
dashboard renders each requirement, reports invalid capability responses and keeps
Run disabled. Schemas reject fabricated approval, duplicate/missing requirements
and extra runner commands. Safe voice phrases navigate only. Existing exact
previews, approval separation, cancellation and owner-scoped history are retained.

Researched and fixed the three Python advisory findings, updating both dependency
ranges and exact lock pins. The dedicated worker and actual patch execution were
not implemented because the prerequisite isolation gate remains blocked. No
environment flag, local fixture report or frontend value can authorize execution.

## B. Architecture, threat model and trust boundaries

The M9 malicious-source/import/script, privilege/escape, socket, filesystem/link,
network/secret, resource, cross-user/replay, duplicate/crash, artifact/log and
supply-chain threats remain in scope. Passing trusted fixtures cannot remove
container escape from this threat model. Do not weaken that requirement.

Target design, not deployed or runtime-verified:

| Responsibility | Identity and boundary |
| --- | --- |
| API/authentication | Existing owner-bound JWT, refresh session, CSRF and GitHub authorization; no Docker control |
| Approval persistence | Immutable single-use grant bound to owner/repo/commit/proposal/hash/profile/policy/expiry/request ID; review alone never grants execution |
| Source acquisition | Trusted read-only GitHub fetcher outside runtime; exact commit/blob and size checks; no lifecycle scripts |
| Scheduling | PostgreSQL transaction converts a valid execution grant into one unique job; no browser-selected command |
| Restricted worker | Separate service identity and job-only database role; no JWT signing key, GitHub token, model credentials or access to user/refresh/connection tables |
| Narrow launcher | Separate privileged service in a dedicated sandbox VM; authenticated worker identity and fixed job-envelope API, never unrestricted Docker HTTP |
| Untrusted runtime | Ephemeral container inside that VM, network none, no control socket, secrets, shared Windows paths, devices or management credentials |
| Result processing | Bounded inert logs, exact observed exits/manifests/cleanup facts; model prose never substitutes for evidence |

Use a separately managed Linux VM or equivalently reviewed isolation service,
without Docker Desktop host-file integration, shared project mounts, application
services or personal workloads. Limit its management endpoint to an authenticated
worker on a restricted management network. Do not expose the Docker daemon on TCP.
The workload network must have no route to management, PostgreSQL, Ollama or GitHub.
The launcher retains privileged Docker control within the dedicated VM, so its
implementation and authentication remain security-critical. No claim of immunity
to hypervisor or kernel vulnerabilities is made. Independently review VM patching,
host integration, trust roots and actual negative tests before admission.

The launcher request must contain only a server-issued job ID and fencing token,
not arbitrary commands, paths, images or mount specifications. It must retrieve
the immutable authorized envelope from a narrow trusted channel, validate all
bindings and select its fixed profile itself. No host checkout is a workspace.

Future lifecycle design: one additive job row per existing preview, owner-bound
idempotency, atomic SQL claim, monotonically increasing fence, bounded lease,
heartbeat, cancellation intent and exact labeled runtime ID. Database and launcher
must both enforce fencing; rejecting stale database writes alone cannot stop a
stale worker from launching a duplicate container. Expired or uncertain applying/
validating jobs must be reconciled against runtime/manifest facts or marked
interrupted, never blindly reapplied. Acknowledge cleanup only after exact owned
resources are absent. No broad container prune or automatic retry after ambiguity.
These lifecycle mechanisms are designed only, not implemented or tested here.

## C. Exact changed files and staging allowlist

Nothing is staged. These are the only source/evidence files intended for review:

```text
README.md
backend/app/api/routes/sandbox.py
backend/app/sandbox/policy.py
backend/app/sandbox/readiness.py
backend/app/sandbox/schemas.py
backend/app/voice/agent.py
backend/requirements-dev.lock.txt
backend/requirements-dev.txt
backend/requirements.txt
backend/security_tests/test_runner_readiness.py
backend/tests/test_sandbox.py
docs/ARCHITECTURE.md
docs/MILESTONE_10_VERIFICATION.md
docs/PROGRESS.md
docs/WINDOWS.md
docs/milestone-10-runtime-evidence.json
frontend/scripts/verify-automation-browser.mjs
frontend/src/components/automation/sandbox-panel.tsx
frontend/src/lib/sandbox.ts
frontend/src/tests/automation.test.tsx
frontend/src/tests/sandbox.test.tsx
```

Exclude environment files, model/audio data, personal data, caches, node_modules,
test screenshots, next-env.d.ts and generated AGENTS.md. The four stash object IDs
are preserved: 3fce76236a951bc34c86aea3c2ec42a651677fd9,
3ddb4687fae40b8a95cceb0b0f5666d21ba954ac,
e38d863d98bab479bb87e0978764f9fcc2c1c18c,
26b23eadaed05d3865e308f4dc9e45e4441156e1.

## D. Database migration status

Head/current remain 0006_sandbox_previews. Live Alembic check detects no new
upgrade operations. Existing users, proposals, previews and audits are preserved.
No 0007_restricted_runner migration is added: the required phase C isolation
approval has not passed, so no executable job/lease queue is introduced. Existing
migration and metadata integration tests remain part of the guarded test suite.

## E. Worker separation evidence

No restricted worker identity or job-only database role is provisioned. The
inspected desktop-linux endpoint is the local Windows Docker named pipe and the
operator command uses the current desktop account. The existing AI worker still
loads application configuration/GitHub access. It is not reused for sandbox work.
There is no new worker startup command or HTTP launcher endpoint. The absence of
these identities is an explicit blocker, not a verified security property.

## F. Image identity and provenance evidence

Existing base distribution: docker.io/library/python, pinned in the unmodified
Dockerfile to sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1.
Existing local fixture image ID:
sha256:753c49dfd11314e64f6abf877c6d5e2f58304ed628215f11855960058d6f5430.
Inspection confirms UID/GID 65532 and the fixed isolated Python probe entrypoint.

Read-only public registry metadata is available for linux/amd64: SLSA builder ID
https://github.com/docker-library, BuildKit build type, Dockerfile source
https://github.com/docker-library/python.git#2a3b794c223ab067d122719541cdd54a068732a5:3.12/slim-trixie,
and five materials. This is metadata retrieval, not independent signature/trust-root
verification. No upstream signature or image approval is fabricated. A local
RepoDigest is still content identity, not proof of approved provenance.

Docker Scout 1.23.1 locally indexed 127 packages. Inventory includes Python 3.12.15,
pip 25.0.1, apt/dpkg, bash/dash, tar and other general utilities. The image is not
an approved minimal hostile-code runtime. Scout's CVE lookup required Docker login
and exited without a vulnerability report. No login or remote account change was
performed. Image vulnerability status is unknown, not clean. No image rebuild,
mutation or package installation inside the image occurred.

## G. Runtime isolation results

Five existing trusted fixtures passed again on Docker 29.6.2 Linux/cgroup v2.
[Raw evidence](milestone-10-runtime-evidence.json) records actual config checks,
non-root/no-new-privileges/capability/seccomp state, failed fixed external/host
database/Ollama connections, named host/socket inaccessibility, 32-PID enforcement,
128 MiB OOM exit 137, timeout/scheduled cancellation termination and exact-container
cleanup. All five probe containers were removed. CPU quota/tmpfs capacity are
observed restrictions, not new CPU or disk exhaustion tests.

Working-tree raw source hashes now include Git's CRLF conversion after merge;
LF-normalized sources match the M9 evidence and the local image ID is unchanged.
This observation is not image-source provenance approval. No malicious repository
code ran on Windows, WSL, the API, worker or runtime. No fixture passing result is
promoted to hostile-code admission. No shared engine/project resource was pruned.

## H. Patch application and validation evidence

No actual approved patch was applied and no application validation was executed.
The harmless M9 tmpfs fixture remains two fixed byte strings plus trusted ast.parse.
It does not prove source acquisition, diff parsing, approved application or imports.
The requested full disposable-repository integration is deliberately not attempted
because the independent isolation prerequisite is unmet.

Future strict applier design: verify the exact immutable approved unified diff by
regenerating artifacts against pinned authorized source; reject unexpected files,
malformed/context-mismatched hunks, binary/protected paths and size violations.
Use exclusive no-follow, directory-relative file creation within a fresh VM tmpfs;
reject symlinks, hard links and unexpected metadata. Verify complete before/after
manifests and never invoke git hooks or shell patch strings. Initial validator must
be a fixed AST-only image tool with no repository imports, package installs or
network fallback. This is a future design, not an implemented executor.

## I. Backend, frontend, CI and browser verification

New tests cover blocked admission independently of environment/fixture success,
fabricated verification, missing/duplicate checks, command injection into metadata,
response mutation, authenticated no-store readiness, safe voice routing, inert
readiness text, invalid-response UI and disabled execution. Standard CI remains
unprivileged with mocked external interactions and no personal model/credential/
Docker requirement. No CI permission or workflow was expanded.

The first frontend run had five failures because the old workbench mock returned
an array for every query, including capabilities, producing an additional invalid-
readiness alert. The mock now returns the real new blocked contract. Existing
assertions were preserved; no application security behavior was weakened.

Final command results and browser outcome are recorded below.

## J. Cancellation and crash recovery

Existing preview cancellation/expiry/idempotency remain supported. Real fixed
container timeout and scheduled harness cancellation passed. They are not durable
application-job cancellation or lease/crash recovery tests. No durable runtime
recovery, stale fence enforcement, lease heartbeat or orphan reconciliation exists.
These remain designed requirements and explicit blockers, without automatic
re-execution of uncertain jobs. M9 finally cleanup limitations remain documented.

## K. Dependency security research and changes

The three M9 findings were researched before changing pins:

- certifi 2026.10.19 removes the affected trust roots, per the
  [reviewed advisory](https://github.com/advisories/GHSA-6q48-6c7w-9gw2).
- cryptography 50.0.2 includes the 50.0.0 PKCS7 security fix and subsequent wheel
  updates, per the [vendor changelog](https://cryptography.io/en/latest/changelog/).
  Application imports use Fernet/InvalidToken; the changed PKCS7/ASN.1 paths are not
  application interfaces. Existing encryption/config/auth regressions verify
  compatibility; upgrading a major version alone is not accepted as evidence.
- pytest 9.0.3 fixes insecure temporary-directory handling, per the
  [vendor changelog](https://docs.pytest.org/en/stable/changelog.html#pytest-9-0-3-2026-04-07).
  Its legacy ini-options configuration remains supported. Pinning this patch
  avoids adopting the separate 9.1 line. Existing fixtures run with warnings as errors.

Binary-wheel resolution changed only these three packages. Source requirements
now require cryptography >=50.0.2,<51, certifi >=2026.10.19 and pytest >=9.0.3,<9.1;
the lockfile pins exact tested versions. pip check passes. Isolated pip-audit of
all 85 pinned packages reports no known vulnerabilities, exit 0. Audit tooling
remains in a separate temporary environment. Pins lack complete artifact hashes;
the audit warns about that limitation. A clean advisory lookup is not a guarantee
against unknown vulnerabilities or compromised artifacts.

Next.js and eslint-config-next remain exactly 16.4.2 with unchanged matching npm
lockfile. Production npm audit is clean. Full npm audit still reports five high
development-tooling entries through braces/micromatch/fast-glob/Next ESLint. No
patched braces version is listed in the
[reviewed advisory](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm);
the suggested forced Next 14
downgrade is not applied. Those findings and unavailable image CVE results remain
release risks rather than suppressed audits.

## L. Windows startup instructions

See [WINDOWS.md](WINDOWS.md#milestone-10-preparation-only-readiness) for dependency
installation, Docker/WSL checks, existing PostgreSQL, migrations, backend/frontend,
Ollama, operator probe/inventory, browser preparation verification and shutdown.
No restricted worker/launcher startup exists while the prerequisite gate is blocked.
Do not add the Docker socket to FastAPI, the AI worker or a workload to bypass this.

## M. Execution gate and scope classification

| Capability | Designed | Implemented | Unit-tested | Integration-tested | Runtime-verified | Enabled |
| --- | --- | --- | --- | --- | --- | --- |
| Six blocked admission requirements | Yes | API/UI | Yes | Authenticated API | No execution claim | Read-only metadata |
| Safe navigation | Existing design | Additional phrases | Yes | Existing preparation browser flow | No new physical speech test | Navigation only |
| Patched Python dependencies | Compatibility reviewed | Three pins/ranges | Regression suite | Guarded PostgreSQL/API | Advisory check only | Local tested environment |
| Restricted worker/launcher identities | Proposed | No | No | No | No | No |
| Durable executable jobs/fencing/recovery | Proposed | No | No | No | No | No |
| Approved patch application/validation | Proposed | No | Proposal checks retained | No execution flow | No | No |
| Hostile-code VM boundary/image approval | Required | No approved environment | Mocks do not establish it | No | No | No |

Execution stays DISABLED. Preparation-only scope is not full runner completion.
API confirmation still denies valid ui_click requests with SANDBOX_UNVERIFIED.
Run remains disabled in the frontend and execution_enabled false in both schema
layers. No environment setting or local report is ingested as execution approval.

## N. Git preservation

No files staged, committed, pushed or merged. No stash was applied, reset, dropped
or deleted, no branch deleted and no Milestone 11 work begun. The report allowlist
is the exact intended review scope. Generated output is excluded and preserved.

## O. Remaining blockers and final results

Provision and independently assess the dedicated VM/service, restricted identities,
authenticated launcher and image trust policy. Obtain an image vulnerability
report and review unnecessary tools. Only then implement migration 0007 and the
job lifecycle, exact acquisition/materialization/applier, fixed validator, separate
single-use confirmation, factual results, durable cancellation/fencing/recovery
and opt-in full fixture integration. General repository execution remains disabled.

| Current check | Actual result |
| --- | --- |
| Full backend suite with warnings as errors | 537 passed in 224.05 seconds, pytest 9.0.3 |
| Independent security suite | 114 passed, including 12 new admission/voice cases |
| Ruff lint/format | Passed, 121 Python files covered |
| Alembic current/head/check | 0006_sandbox_previews; no pending schema operations |
| Migration/auth/GitHub/preview regressions | Included in full guarded PostgreSQL suite |
| pip check | No broken requirements |
| Python advisory audit | Zero known findings across 85 pins; exit 0 |
| Frontend unit suite | 171 passed across 11 files, four new readiness cases |
| ESLint / TypeScript | Passed, zero lint warnings |
| Production build | Next.js 16.4.2 passed |
| npm production audit | Zero vulnerabilities, exit 0 |
| npm full audit | Five existing high development-tooling findings, exit 1 |
| Trusted real Docker fixtures | Five passed, exact-container cleanup confirmed |
| Local image SBOM inventory | 127 packages indexed |
| Image CVE audit | Blocked by Docker login requirement; no clean result claimed |
| Independent provenance/worker/VM approval | Not established |
| Actual approved-patch execution integration | Not attempted; admission gate remains blocked |

The extended existing Edge script passed against real production Next.js,
FastAPI and the guarded PostgreSQL test database with a disposable account and
controlled GitHub/Ollama. It asserted all six admission requirements, blocked
admission, disabled Run, exact preview, review/rejection/cancellation, restored
history, secret-path denial and voice navigation. Observed zero execution/confirm
requests, zero page errors and no horizontal overflow at mobile width. Desktop
and mobile screenshots were visually inspected; element captures include the
existing sticky navigation overlay. They remain ignored verification artifacts.
Only the fixture's owned account and child servers were cleaned up. This is
preparation UI integration, not the forbidden unverified execution flow.

No personal GitHub credentials, real local Ollama inference, microphone or Piper
hardware acceptance was re-run. No remote CI was triggered because nothing was
pushed. The exact 21-file allowlist matches the working tree; no files staged.
Generated caches/screenshots remain excluded. Four stash object IDs match the
starting inventory. No runtime probe container remains and codemate-postgres is
preserved. Source review found no actual local credential-value matches.
