# Local portfolio release checklist

This checklist is evidence-driven. MILESTONE_12_VERIFICATION.md is the source of
actual outcomes; an item here is not a passing result by itself. Public production
readiness requires a separate threat/deployment review.

## Required local checks

- Confirm expected branch/HEAD, empty index and four preserved stash hashes.
- Install the exact backend lock and npm ci. Review dependency-path/version diffs;
  do not use forced audit fixes or replace populated local environment files.
- Run pytest with warnings as errors against only codemate_test_db/test role.
- Run Ruff lint/format, pip check, Alembic heads/current/check; head remains 0006.
- Run Vitest, zero-warning ESLint, TypeScript and normal Next.js production build.
- Run Python advisory audit, npm audit --omit=dev and npm audit. Record nonzero
  findings, dates and applicability, including historical findings that changed.
- Run owned-account Edge auth/GitHub/AI/metrics and automation suites sequentially.
- Verify desktop/tablet/mobile widths, labels, keyboard focus, dialog Escape,
  reduced motion and log/diff scrolling. Record manual accessibility limitations.
- Inspect sanitized screenshots locally; keep generated results ignored.
- Record real-model, real-GitHub, synthetic-audio and physical-audio status separately.
- Repeat comparable bounded benchmarks without overwriting Milestone 11 artifacts.
- Verify current source/diff/hash binding, expiry, replay, cross-user/RBAC/CSRF
  denial and sanitized logging. No token or private source in report or screenshots.

## Non-negotiable execution and permissions checks

- GitHub App retains read-only permissions and selected installation authorization.
- execution_enabled/applied remain false, validation remains not_executed.
- Six admission blockers stay visible; valid confirmation returns SANDBOX_UNVERIFIED.
- No feature flag, voice/model command, queue, launcher or Docker endpoint bypass.
- No repository files, commits, pushes or automatic deployments created by the app.
- No Docker socket/privileged mount, unrestricted shell or untrusted standard-CI job.

## Deployment distinction

Use the existing guarded PostgreSQL helper and loopback application processes.
Production credentials must be independent and non-placeholder. Secure cookies,
explicit HTTPS origins and trusted ingress assumptions remain documented. TLS,
backup/restore drill, retention/alerts, formal accessibility and external security
review are not certified by a successful local browser demonstration. Rehearse
failures honestly and keep typed navigation available without microphone/models.

## Review and handoff

Record exact changed files and a narrow staging allowlist in the verification
report. Review whitespace, secrets, generated artifacts and unchanged stashes.
Do not stage, commit, push, merge, delete or deploy without explicit approval.
Classify A local demonstration ready, B ready with limitations, or C blocked;
choose from actual evidence, not the fact that the roadmap has twelve milestones.
