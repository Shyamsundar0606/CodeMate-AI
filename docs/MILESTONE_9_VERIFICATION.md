# Milestone 9 verification, 2026-10-22

Status: fixture-only infrastructure preparation. Application execution DISABLED.
The verified runner definition of done is not met. This report does not certify
hostile repository execution or claim the complete worker lifecycle exists.

## 1. Actual implementation and repository audit

Started from clean main at 2bc6b71 and created
feature/milestone-9-isolated-execution. Existing README, architecture, Windows,
progress, M7 final verification and M8 verification documents, automation source,
sandbox policy/service/routes/models, authorization, AI worker, migrations,
Docker Compose, guarded database fixtures and CI were inspected. M8 is genuinely
preparation-only: confirmation always returns SANDBOX_UNVERIFIED, response schemas
require false/not_executed and there is no launcher, executable queue or worker.
The existing AI worker has application credentials and cannot serve as the
restricted sandbox worker. README's stale migration table was corrected to 0006.

The new operator prototype builds offline, inspects actual restrictions, executes
five trusted harmless fixtures, captures bounded facts and removes its containers.
Its build context excludes everything except Dockerfile and probe.py. It is not
reachable from the application. A new API capability reason explains why a passing
fixture probe is insufficient. Three additional safe voice phrases only navigate.
CI lints the prototype and unit-tests its contract without requiring Docker.

User approved a minimal Next.js security update after npm audit and the production
build detected critical advisories in 16.4.0. Next.js and eslint-config-next are now
exactly pinned to 16.4.2, with the matching lockfile update. No force audit repair,
major backend dependency upgrade or unrelated application change was performed.

## 2. Architecture and security boundaries

See [the threat model](MILESTONE_9_THREAT_MODEL.md) for assets, hostile actors,
trust boundaries, controls, required lifecycle design and stop conditions.

Designed target: UI -> authenticated API -> durable exact confirmation -> restricted
worker -> trusted launcher -> disposable isolated environment -> factual results
and PostgreSQL audit history. API, approval DB, source acquisition, worker, Docker
control plane, untrusted runtime, GitHub credentials, PostgreSQL, Ollama and
Windows/WSL are distinct domains. No model controls commands or declares success.

Implemented prototype: an explicitly opted-in operator process controls the local
Docker engine, executes only image-baked fixture cases and emits a local report.
It does not have the target worker identity separation. Ordinary Docker Desktop
containers share the Linux VM/kernel and are not equivalent to a dedicated hardened
VM. The shared development engine has other project images and host integration.
This environment does not establish the required hostile-code boundary.

## 3. File changes and exact review/staging allowlist

No files were staged. Review only these files for a future explicit staging step:

```text
.github/workflows/main.yml
README.md
backend/app/sandbox/policy.py
backend/app/voice/agent.py
backend/security_tests/test_sandbox_gate.py
backend/security_tests/test_sandbox_prototype.py
docs/ARCHITECTURE.md
docs/MILESTONE_9_THREAT_MODEL.md
docs/MILESTONE_9_VERIFICATION.md
docs/PROGRESS.md
docs/WINDOWS.md
docs/milestone-9-runtime-evidence.json
frontend/package.json
frontend/package-lock.json
infrastructure/sandbox/.dockerignore
infrastructure/sandbox/Dockerfile
infrastructure/sandbox/probe.py
infrastructure/sandbox/verify.py
```

Generated files, caches, environment files, credentials, frontend/next-env.d.ts and
frontend/AGENTS.md are excluded. No personal browser/session or source repository
is used by the probe. Existing local images/build cache are retained, not staged.
All four original stashes are preserved. No commit, push, merge, reset, clean,
stash operation or branch deletion was performed. No Milestone 10 work was started.

## 4. Database migration and existing API

No migration 0007 is added: no application execution jobs or leases are introduced.
Head remains 0006_sandbox_previews. Live Alembic current and metadata check pass.
Existing schema/records are not rewritten. Migration roundtrip tests target only
the existing guarded codemate_test_user/codemate_test_db on 127.0.0.1:5433.

M8 owner/repository authorization, exact patch regeneration, source/hash checks,
CSRF/session binding, idempotency, preview expiry, cancellation and history remain.
The confirmation endpoint still denies execution even for an otherwise valid
ui_click binding. No request accepts shell text, host paths or Docker operations.
No flag, report file or voice command can enable execution.

## 5. Runtime image and actual configuration

Prototype version: m9-fixture-v1. Base:
python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1.
Local tested image ID:
sha256:753c49dfd11314e64f6abf877c6d5e2f58304ed628215f11855960058d6f5430.
This local immutable identity is not an independently verified registry provenance
claim. BuildKit emitted local build attestations; these were not approved as
upstream signatures or a supply-chain audit. The base still includes general Python
image tools; it is not an approved minimal hostile-code runtime. No image is
registered as approved in application policy, which retains image_digest null.

Docker Engine 29.6.2, desktop-linux, Linux x86_64, cgroup v2, built-in seccomp;
WSL default Ubuntu-24.04 version 2. Docker Desktop was initially stopped and was
started without modifying other project containers. Only codemate-postgres was
running at inspection and remained healthy on the existing port 5433.

Actual inspected restrictions: UID/GID 65532, non-privileged, all capabilities
dropped, no-new-privileges, built-in seccomp filter, read-only root, private PID
and cgroup namespaces, IPC none, network none, no sensitive mounts/devices/socket/
ports, no application environment, 128 MiB memory and swap cap, 0.5 CPU, 32 PIDs,
64 open files, 8 MiB noexec/nosuid/nodev workspace tmpfs, no runtime log driver.
Output capture caps each pipe at 32 KiB and has finite subprocess deadlines.
Unknown inherited environment names, including proxy injection, reject inspection.
The fixed probe needs no npm/pip install, repository hooks, shell or network.

## 6. Actual isolation evidence and limits

Raw bounded facts and exact source hashes are in
[milestone-9-runtime-evidence.json](milestone-9-runtime-evidence.json).

| Real fixture | Observed result | Scope limit |
| --- | --- | --- |
| Baseline | Exit 0; UID/GID, read-only-root attempt, zero capabilities, no-new-privileges and seccomp filter checks passed | No kernel/container escape proof |
| Network/secret/socket checks | Fixed external IP, host database and Ollama attempts failed; named host paths/socket absent or permission-denied; no named app credentials in environment | Does not enumerate every host path, secret or network destination |
| PID exhaustion | Fork rejected after 31 children under 32-PID limit; children reaped | Fixed bounded fixture, not a host fork bomb |
| Memory exhaustion | OOMKilled true and actual runtime exit 137 under 128 MiB limit | No host-wide availability guarantee |
| Timeout | Three-second client deadline followed by exact container kill; runtime stopped, exit 137 | No durable worker timeout/recovery |
| Scheduled cancellation | One-second harness cancellation followed by exact container kill; runtime stopped, exit 137 | Not application/API cancellation of a job |
| Cleanup | All five exact containers removed; label queries empty | Finally cleanup cannot survive operator-process death or daemon outage |
| Source fixture | Original bytes unchanged; replacement file hash checked; trusted ast.parse returned normally | Not GitHub acquisition, strict patch application or execution authorization |

CPU quota, memory/PID cgroup values and tmpfs capacity are observed; PID/memory
limits were additionally exercised. CPU contention, disk exhaustion, custom seccomp,
privilege escalation, malicious materialization/link races and VM escape were not
tested. An initial probe failed because Path.exists raised PermissionError for
/root/.ssh; the probe now classifies inaccessible paths correctly. Restrictions
were not weakened. Its failed containers were also removed.

## 7. Automated checks

Historical M8 baseline was 496 backend and 167 frontend tests. An initial full
M9 run passed 499 backend cases before prototype-contract tests were added.
Final full-suite and post-update frontend results are recorded below.

Prototype contract tests cover mutable/injected image/command rejection, actual
configuration drift, host mounts, unsafe image environment/entrypoint, cleanup on
inspection failure, bounded output, host environment filtering, explicit operator
opt-in and inability of a passing report to enable application execution. These
are unit tests, not evidence of Docker isolation. Standard CI has no new Docker,
socket, model, personal credential or privileged public-PR requirement.

Checks run: pytest -q -W error --tb=line; Ruff lint/format for backend and prototype;
Alembic heads/current/check and migration integration tests; pip check; Vitest;
ESLint with zero warnings; TypeScript; normal production build; npm audits and an
isolated pip-audit of the pinned backend requirements. See final results below.

## 8. Real integration and patch behavior

Five real container fixtures ran, and the existing API/PostgreSQL regression suite
passed. There was no integrated approved-patch -> queue -> materialization ->
validation -> PostgreSQL result -> browser reload run. No personal GitHub repository
or user checkout was a patch target. The prototype's two known tmpfs files are not
an implementation of strict patch application. No original checkout file was
changed by a runtime. No application exit code, stdout/stderr or passed validation
is invented. The UI continues to display preparation records only.

## 9. Execution gate decision

DISABLED. Container fixture success is insufficient. Of the fifteen required gates,
local restriction checks provide partial runtime/resource/network evidence and
the existing API gate has regression coverage. Security review, worker separation,
approved image provenance, complete host/FS containment, single-use execution
authorization, approved patch application, real integrated exit reporting, durable
cancellation/cleanup, crash/duplicate recovery and real fixture integration are
not established. Relevant unit tests alone cannot enable a profile. No general
repository execution or even application Python-syntax execution is enabled.

## 10. Vulnerabilities and limitations

Next.js 16.4.0 initially produced a fatal build security warning and npm reported
critical advisories GHSA-2464-fhr4-w9xw and GHSA-673q-mjm6-r5xr, plus
GHSA-p3m5-59mp-jv5r. The approved 16.4.2 patch removes the current production npm
audit findings. Five high dev-tooling findings remain in the existing
braces/micromatch/fast-glob/Next ESLint chain. No forced breaking downgrade was used.

The isolated Python audit reported five entries in three pinned packages, with
duplicate IDs for cryptography and pytest. Unique findings: certifi 2026.7.22,
PYSEC-2026-4320 (reported fix 2026.10.19); cryptography 49.0.0,
PYSEC-2026-3552 (reported fix 50.0.0); pytest 8.4.2, PYSEC-2026-1845
(reported fix 9.0.3). These are reported dependency findings, not demonstrated
exploitation of this application. Backend dependency changes require a separately
reviewed compatibility update. The project venv/lockfile were not modified by the
audit; pip-audit ran from a new temporary environment. Advisory exit 1 is not a
clean audit. Neither pip check nor passing tests supersede these findings.

The prototype has no durable leases, heartbeats, queue, orphan recovery, secret
redactor, artifact ingestion or multi-user execution service. A stopped daemon or
operator crash can leave its labeled containers until manual inspection. Default
seccomp is observed, not a reviewed custom syscall policy. Never accept untrusted
images or source through this operator tool. Release security remains conditional
on the outstanding dependency findings and isolation review.

## 11. Windows startup and verification

Exact PowerShell build, immutable ID inspection, opt-in fixtures, PostgreSQL,
migration, backend, existing AI worker, frontend and Ollama instructions are in
[WINDOWS.md](WINDOWS.md#milestone-9-operator-only-fixture-verification).
There is no executable sandbox-worker command. Do not mount a Docker socket into
FastAPI, reuse the AI worker for code execution or disable security controls.

## 12. Remaining Milestone 9 work

Provision and review a dedicated sandbox VM/service and restricted identities;
approve upstream image provenance/minimal contents; verify hostile isolation and
remaining negative tests there. Only then implement the minimal launcher handoff,
additive durable job/lease migration, atomic claims/fencing/recovery, authenticated
credential-free exact source acquisition, strict patch application, actual bounded
validation/log collection, explicit UI confirmation and durable cancellation.
Complete the requested real PostgreSQL/UI fixture integration and all failure/
crash/duplicate scenarios before enabling only a tested narrow profile. General
repository execution must remain disabled. Address dependency findings separately.

## 13. Final verification results

| Check | Actual final result |
| --- | --- |
| Full backend pytest, warnings as errors | 524 passed in 236.81 seconds |
| Post-inspection-tightening prototype contract rerun | 25 passed; no Docker or database |
| Ruff lint and format | Passed, 119 Python files covered |
| Alembic current/head/check | 0006_sandbox_previews; no new upgrade operations |
| Migration roundtrip and database tests | Included in passing full guarded PostgreSQL suite |
| pip check | No broken requirements |
| Vitest after Next.js update | 167 passed, 11 files |
| ESLint / TypeScript after update | Both passed, zero lint warnings |
| Normal production build after update | Next.js 16.4.2 passed, all routes generated |
| npm production audit after update | Zero vulnerabilities |
| npm full audit after update | Five existing high dev-tooling findings, exit 1 |
| Isolated pip-audit of pinned backend requirements | Five entries, three unique IDs in three packages; exit 1 |
| Final real Docker fixture suite | All five cases passed; every owned container removed |
| Application patch/validation integration | Not run; gate remains disabled |
| Personal browser/GitHub/Ollama acceptance | Not re-run; no claim of new live-model quality |

The final full backend suite began before the last prototype working-directory/
environment inspection tightening. The affected 25 contract tests and all five
real Docker fixtures were rerun successfully afterward. No application runtime
logic changed after that full suite. CI was not run remotely because nothing was
pushed. Initial root-directory Ruff invocation misclassified existing app imports;
running the documented backend-directory command passed without rewriting existing
files. The initial Next.js 16.4.0 build failure was resolved by the approved patch,
not by suppressing the security warning.

| Capability | Designed | Implemented | Unit-tested | Integration-tested | Runtime-verified | Enabled |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed operator fixtures | Yes | Yes | 25 contract cases | Five local containers | Listed controls only | Explicit local opt-in only |
| Immutable local prototype image identity | Yes | Yes | Inspection drift tests | Offline build and actual launches | Local ID only | No approved application image |
| M8 preparation/confirmation denial | Existing | Retained | Gate/security cases | Guarded PostgreSQL/API suite | No code execution | Preparation only |
| Restricted worker and durable job lifecycle | Target only | No | No | No | No | No |
| Approved source materialization/patch application | Target only | No | Existing proposal checks only | No execution integration | No | No |
| Actual application validation/results/UI progress | Target only | No | Disabled schemas retained | No execution integration | No | No |
| Hardened hostile-code boundary and provenance | Required | No approved environment | Not established by mocks | No | No | No |

Working-tree review contains exactly the 18 allowlisted files. The index is empty;
all changes remain unstaged. Untracked directories were expanded, including the
ignored infrastructure/sandbox/__pycache__ generated by contract imports. Caches
are preserved and excluded. frontend/next-env.d.ts is unchanged and frontend/AGENTS.md
is absent. Four original stash object IDs match the initial inventory. No runtime
probe container remains. Existing PostgreSQL and other project containers are
untouched by cleanup.
