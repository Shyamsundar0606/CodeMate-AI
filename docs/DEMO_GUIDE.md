# CodeMate AI portfolio demonstration

## Scope and narrative

A developer encounters a failing GitHub Actions workflow. CodeMate analyzes bounded
logs, explains pinned source and proposes a reviewable correction. A person reviews
the diff and may record approval. The exact execution preview remains blocked
because independent sandbox security verification is incomplete. No repository
file is changed and no validation is executed.

Automated demonstrations use deterministic GitHub/Ollama fixtures, a real local
production frontend/FastAPI and guarded PostgreSQL. Say "controlled model response"
when presenting those results. Real Ollama acceptance is a separate check; fixture
success does not establish real-model quality. Never present a proposed patch as
verified, applied or deployed.

## Preparation

Follow WINDOWS.md and DEPLOYMENT.md for the existing venv, locked dependencies,
local secrets, PostgreSQL and additive migrations. Preserve populated .env files.
Use only authorized non-sensitive repositories for a personal live demonstration.
Keep PostgreSQL, Ollama and metrics private; do not publish this profile.
No fixed demo password or default administrator is shipped.

From the project root, with free ports 3000/8001 and no concurrent backend tests:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File infrastructure/verify-demo.ps1
```

This builds the current normal production frontend and verifies the controlled
source/proposal/review/preview journey in headless Edge. It owns its account and
child processes. It refuses occupied ports, cleans exact owned accounts and leaves
ignored screenshots in frontend/test-results. A separate existing acceptance suite:

```powershell
Set-Location frontend
npm.cmd run test:e2e
```

That suite builds .next-e2e and verifies authentication, account preferences,
repository/Actions investigation and protected operations. Run the normal production
build afterwards before standalone typecheck. Neither command needs personal
GitHub credentials, a microphone, GPU or real Ollama. They require installed Edge.
Do not run the two browser suites or backend pytest concurrently against the DB.

## Suggested ten-minute walkthrough

1. Explain the problem and read-only GitHub boundary. Label fixtures visibly in
   narration and use the sanitized octocat/secure-demo example only.
2. Register and sign in with a unique disposable account. Show profile/settings
   and keyboard-accessible navigation. Explain memory-only access tokens and
   HttpOnly refresh rotation without displaying tokens or browser cookies.
3. Connect the controlled authorized installation and explore repositories,
   branches, pull requests, issues and failed Actions job logs. Logs remain inert.
4. Open AI diagnosis, inspect evidence citations and explain what the controlled
   report supports. Describe missing evidence and inference limitations.
5. Inspect main.py at its pinned commit. Request a source explanation, follow its
   cited lines, and reload without regenerating the explanation.
6. Request the addition correction. Read the exact diff and its unverified risks.
   Reject one proposal and generate another to demonstrate separate decisions.
7. Open the approval dialog. Check repository, base SHA and patch hash, then record
   review approval. Explain that approval grants no execution or GitHub write access.
8. Prepare the exact execution preview. Show before/after hashes and all six
   blocked admission requirements. Point out the disabled Run and no-test output.
9. Cancel the preview and reopen persisted history. Use typed voice navigation to
   show sandbox readiness. Voice cannot approve a run.
10. Explain liveness/readiness, safe correlation and ADMIN-only aggregate metrics.
    Finish by signing out and showing protected-page denial.

## Separate real-service and hardware checks

For real Ollama, check the existing /api/tags and run the documented opt-in
backend/scripts/verify_local_ai.py against its harmless controlled GitHub fixture.
It is real local inference with controlled evidence, not real GitHub acceptance.
Do not download a model to make a demo pass. Validate every citation/claim.

For real GitHub, sign in normally, authorize the App on a deliberately selected
repository and read its pinned source and an Actions result. Do not revoke personal
permissions merely to simulate an outage; use controlled denial fixtures instead.
No real GitHub acceptance is claimed unless separately recorded in the report.

For physical audio, get consent before recording. Check microphone permission,
record a short non-sensitive command, inspect the transcript before sending, and
optionally hear Piper output. Test denied permission/no device using typed input.
Synthetic Piper-to-whisper audio is not evidence of microphone/speaker testing.
Suggested commands: show my repositories, explain this source file, show my failed
workflow, open my automation history, show sandbox readiness, explain latest
validation status. Ambiguous/unsupported intents must ask or navigate safely.

## Failure rehearsal and presentation safety

Show model-unavailable feedback without disabling unrelated features. Demonstrate
rate-limit/retry messaging with controlled fixtures. Do not retry a timed-out
mutation blindly: reload persisted state first. Distinguish HTTP request IDs from
authorization or idempotency tokens. Never show populated environments, credentials,
private source, personal installation names or original logs in public screenshots.
If a flow fails, state the failure rather than editing a screenshot or fabricating
success. Current exact results and omissions are in MILESTONE_12_VERIFICATION.md.
