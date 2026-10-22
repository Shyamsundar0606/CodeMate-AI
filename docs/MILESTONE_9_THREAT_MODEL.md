# Milestone 9 threat model and architecture decision

Reviewed locally on 2026-10-22. This is an engineering assessment, not an
independent security certification. Execution remains disabled.

## Assets, actors and boundaries

Assume repository authors, dependencies, AI patches, Python imports, Node scripts,
test output and generated artifacts are hostile. Protect host files and services,
GitHub credentials, signing secrets, account isolation, approval integrity and
availability. A compromised runtime image or privileged launcher is also in scope.

| Boundary | Trust and required separation |
| --- | --- |
| Browser to FastAPI | Existing JWT, cookie ownership, CSRF, Origin and strict schemas; browser text never selects a command |
| API to approval database | API owns authorization and exact immutable M8 previews; no Docker access |
| Trusted source acquisition to worker | Read-only authorized GitHub access outside workload; pinned regular blobs and hashes only; no tokens in workload |
| Restricted worker to launcher | Future authenticated narrow job envelope, fixed profile, no host paths or shell; worker must not inherit API credentials |
| Launcher to Docker control plane | Privileged operator boundary; local Docker endpoint can control the host VM; never exposed to workload or public API |
| Container to Linux kernel/VM | Containers share the Docker Desktop kernel; container controls alone do not establish escape resistance |
| Docker Desktop to Windows/WSL | Shared local development engine has other workloads and host integration; dedicated sandbox VM/service separation is not established |
| Workload to PostgreSQL/Ollama/GitHub | No network, credentials or routes; application DB and model stay outside execution |

The existing AI worker has application configuration and GitHub access. It is not
a suitable sandbox worker. Do not extend it with Docker control. The target is a
separate restricted orchestration identity and minimal trusted launcher in a
dedicated execution environment, with authenticated result handoff to PostgreSQL.

## Threat register

| Threat | Current/prototype control | Remaining verification |
| --- | --- | --- |
| Malicious imports, JS, lifecycle scripts | API executes none; probe accepts only fixed trusted fixtures | Never enable pytest/imports/install scripts without isolated worker review |
| Prompt injection in source/logs | Model cannot select commands; probe results are facts, not model summaries | Future bounded redacted result collector and inert UI |
| Traversal, absolute paths, Git metadata, binary or malformed patches | Existing M7 path/blob/hash validation; probe has no source input | Race-resistant materializer, strict diff regeneration and exact manifests |
| Symlinks, junctions, hard links | No host checkout or source mounts; fresh tmpfs probe files | Real hostile materialization and link-race tests before repository execution |
| Credential theft and host file escape | No supplied host environment or mounts; fixed absent-path probes | Absence checks do not prove all host paths inaccessible or kernel escape resistance |
| Docker socket/control abuse | Standalone operator tool only; no socket in container/API | Dedicated launcher identity, service authentication and host isolation review |
| Network exfiltration | Network none plus real fixed connection attempts | Dedicated environment ingress/control-plane separation |
| Privilege escalation | Non-root, dropped caps, no-new-privileges, default seccomp | Custom syscall review, kernel/VM security review; no claim of escape-proof Docker |
| Fork bomb, memory, CPU, disk, output exhaustion | Fixed bounded probes under cgroups/tmpfs/time/output limits | CPU contention and whole-engine/host denial-of-service resistance |
| Cross-user access, replay, tampering | Existing owner-bound preview and hard confirmation denial | Independent short-lived execution grant and single-use queue transaction |
| Duplicate execution | No executable queue exists | Atomic claim, unique execution identity, lease fencing and runtime identity |
| Worker crash/restart | No application worker launches jobs | Never retry uncertain application; reconcile exact runtime or mark interrupted |
| Cancellation/orphan cleanup | Probe owns unique labeled containers, removes only their exact IDs | Durable cancellation, orphan reconciliation and failure recovery across process death |
| Untrusted artifacts/log secrets | Probe emits only fixed booleans/hashes, bounded capture | No artifact extraction; future redaction cannot guarantee removal of all secrets |
| Image/dependency supply chain | Base digest pinned, local image ID and source hashes recorded | Registry provenance, signatures/attestations, vulnerability audit, minimal approved image |

## Architecture decision and stop condition

First implement an offline, opt-in, fixture-only Docker prototype outside the
application. Build from the already available digest-addressed Python image with
no dependency installation. Inspect actual launch configuration and test harmless
restrictions. A passing probe is not an execution readiness attestation and cannot
change API capabilities. There is no enable flag or runtime report upload endpoint.

The local shared Docker Desktop environment does not demonstrate worker identity
separation, image provenance or a reviewed hostile-code VM boundary. These are
essential blockers. Stop before adding an executable queue, migration 0007 or
repository materializer if those controls remain unverified. Retain M8 schema and
confirmation denial. Do not add dormant execution paths that a setting could enable.

Future durable work should extend the existing preview identity with a single-use
authorized job row, atomic SQL claim and fencing token, lease/heartbeat deadlines,
bounded attempts, cancellation intent and immutable runtime identity. Recovery of
an uncertain applying/validating job must reconcile the labeled runtime and exact
manifest or mark interrupted, never automatically reapply. Store real exit/log/
cleanup facts separately from model text. This design is not implemented here.
