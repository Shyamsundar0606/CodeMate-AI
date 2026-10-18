import base64
import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from sqlalchemy import delete, func, select

from app.ai.errors import AIError
from app.automation.graph import build_graph
from app.automation.policy import EXECUTION_MESSAGE, digest, reject, safe_path, text_file
from app.automation.schemas import Proposal, SessionView
from app.automation.source_scan import python_reason
from app.integrations.github.exceptions import GitHubError
from app.integrations.github.logs import redact_logs
from app.models.automation import (
    AutomationAudit,
    AutomationBudget,
    AutomationProposal,
    AutomationSession,
)
from app.services.voice_service import serialized


class AutomationService:
    def __init__(self, db, settings, user_id, engine, ollama, github_factory):
        self.db, self.settings, self.user_id = db, settings, user_id
        self.engine, self.ollama, self.github_factory = engine, ollama, github_factory
        self.github = None

    def gh(self):
        if self.github is None:
            self.github = self.github_factory()
        return self.github

    def audit(self, session, event):
        self.db.add(AutomationAudit(session_id=session.id, event=event))

    def clean_text(self, value, *, source_path=None, grounded_excerpt=False):
        secrets = [self.settings.jwt_secret_key.get_secret_value()]
        if self.github:
            secrets.append(self.github.token)
        if self.settings.github_client_secret:
            secrets.append(self.settings.github_client_secret.get_secret_value())
        if source_path and source_path.endswith(".py"):
            reason = python_reason(value, secrets)
            if reason:
                raise reject(
                    f"Source file {source_path} rejected: {reason}. "
                    "Remove embedded credentials or unsafe text and retry; "
                    "do not submit secret files."
                )
            return value
        normalized = value.replace("\r\n", "\n")
        clean, _, changed = redact_logs(
            normalized.encode(), False, secrets, assignment_values=not grounded_excerpt
        )
        if changed or len(clean) != len(normalized):
            raise reject(
                "Content contains credential patterns or unsafe control "
                "characters; select another file."
            )
        return value

    def budget(self):
        now = datetime.now(UTC)
        row = self.db.get(AutomationBudget, self.user_id)
        if row is None:
            row = AutomationBudget(user_id=self.user_id, window=now, count=0)
            self.db.add(row)
        if (now - row.window).total_seconds() >= 60:
            row.window, row.count = now, 0
        if row.count >= 6:
            raise AIError(
                "AUTOMATION_RATE_LIMIT", "Wait one minute before another automation request.", 429
            )
        row.count += 1
        self.db.execute(
            delete(AutomationSession).where(
                AutomationSession.user_id == self.user_id, AutomationSession.expires_at < now
            )
        )
        self.db.commit()

    def owned(self, identity):
        row = self.db.scalar(
            select(AutomationSession).where(
                AutomationSession.id == identity, AutomationSession.user_id == self.user_id
            )
        )
        if row is None or row.expires_at <= datetime.now(UTC):
            raise AIError(
                "AUTOMATION_UNAVAILABLE", "Automation session is unavailable or expired.", 404
            )
        return row

    def authorize(self, row):
        gh = self.gh()
        if gh.item.id != row.connection_id:
            raise reject("GitHub connection changed. Create a new automation session.", 409)
        owner, repo = row.repository.split("/")
        gh.repository(owner, repo, row.installation_id)

    def create(self, body):
        with serialized(self.engine, self.user_id):
            self.budget()
            existing = self.db.scalar(
                select(AutomationSession).where(
                    AutomationSession.user_id == self.user_id,
                    AutomationSession.request_id == body.request_id,
                )
            )
            if existing:
                expected = existing.context["input"]
                if expected != body.model_dump(mode="json"):
                    raise reject(
                        "Request identifier already belongs to a different workspace.", 409
                    )
                self.authorize(existing)
                return self.view(existing)
            count = self.db.scalar(
                select(func.count())
                .select_from(AutomationSession)
                .where(AutomationSession.user_id == self.user_id)
            )
            if count >= 10:
                raise reject(
                    "Ten active snapshots allowed. Wait for expiration before creating another.",
                    429,
                )
            gh = self.gh()
            metadata = gh.repository(body.owner, body.repo, body.installation_id)
            root = f"/repos/{body.owner}/{body.repo}"
            evidence = {}
            if body.workflow_run_id:
                run = gh.run(body.owner, body.repo, body.installation_id, body.workflow_run_id)
                sha = run.sha
                evidence["workflow"] = (
                    f"Run {run.id}: {run.status}; conclusion {run.conclusion}; commit {sha}"
                )
                jobs = gh.resource(
                    body.owner, body.repo, body.installation_id, "jobs", 1, 10, run_id=run.id
                ).items
                for job in jobs[:2]:
                    evidence[f"job:{job.id}"] = self.clean_metadata(
                        f"{job.name}: {job.status}; conclusion {job.conclusion}"
                    )
                    if job.status == "completed" and job.conclusion == "failure":
                        try:
                            evidence[f"log:{job.id}"] = gh.logs(
                                body.owner, body.repo, body.installation_id, job.id
                            )["content"][:2000]
                        except AIError:
                            raise
                        except GitHubError as exc:
                            if exc.status_code != 404:
                                raise
                            evidence[f"log:{job.id}"] = "Job logs unavailable."
            else:
                commit, _ = gh._json(
                    root + "/commits/" + quote(metadata.default_branch or "HEAD", safe="")
                )
                sha = commit.get("sha") if isinstance(commit, dict) else None
            if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha):
                raise reject("GitHub did not supply a supported exact commit SHA.", 502)
            commit, _ = gh._json(root + "/git/commits/" + sha)
            tree_sha = commit.get("tree", {}).get("sha") if isinstance(commit, dict) else None
            if not isinstance(tree_sha, str) or not re.fullmatch(r"[0-9a-f]{40}", tree_sha):
                raise reject("GitHub commit tree is malformed.", 502)
            tree, _ = gh._json(root + "/git/trees/" + tree_sha, {"recursive": "1"})
            if (
                not isinstance(tree, dict)
                or tree.get("truncated") is not False
                or not isinstance(tree.get("tree"), list)
                or len(tree["tree"]) > 5000
            ):
                raise reject(
                    "Repository tree is truncated or exceeds 5,000 entries. Select "
                    "a smaller repository."
                )
            entries = {}
            for entry in tree["tree"]:
                if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
                    raise reject("Malformed repository tree.", 502)
                key = entry["path"].casefold()
                if key in entries:
                    raise reject("Case-colliding repository paths are unsupported.")
                entries[key] = entry
            files = {}
            for name in body.paths:
                safe_path(name)
                entry = entries.get(name.casefold())
                if (
                    not entry
                    or entry["path"] != name
                    or entry.get("type") != "blob"
                    or entry.get("mode") != "100644"
                ):
                    raise reject(
                        "Selected file is missing, executable, symlinked or not a "
                        "regular source blob."
                    )
                # No local filesystem is materialized. Ancestor tree entries must be real trees.
                parts = name.split("/")
                for i in range(1, len(parts)):
                    ancestor = entries.get("/".join(parts[:i]).casefold())
                    if (
                        not ancestor
                        or ancestor.get("type") != "tree"
                        or ancestor.get("mode") != "040000"
                    ):
                        raise reject("Non-directory source ancestor rejected.")
                blob_sha = entry.get("sha", "")
                if (
                    not re.fullmatch(r"[0-9a-f]{40}", blob_sha)
                    or not isinstance(entry.get("size"), int)
                    or not 0 <= entry["size"] <= 12000
                ):
                    raise reject("Source blob exceeds its budget or is malformed.")
                blob, _ = gh._json(root + "/git/blobs/" + blob_sha)
                try:
                    if blob.get("encoding") != "base64" or blob.get("sha") != blob_sha:
                        raise ValueError()
                    raw = base64.b64decode(blob["content"].replace("\n", ""), validate=True)
                    if len(raw) != entry["size"]:
                        raise ValueError()
                    if hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest() != blob_sha:
                        raise ValueError()
                except (KeyError, ValueError, TypeError, AttributeError) as exc:
                    raise reject("Source blob integrity check failed.", 502) from exc
                try:
                    files[name] = self.clean_text(text_file(raw), source_path=name)
                except AIError as exc:
                    if not exc.detail["message"].startswith("Source file "):
                        raise reject(
                            f"Source file {name} rejected: credential pattern, "
                            "unsafe text or unsupported encoding. "
                            "Select a safe text file and retry."
                        ) from None
                    raise
            if sum(len(c.encode()) for c in files.values()) > 24000:
                raise reject("Selected source context exceeds 24 KB.")
            row = AutomationSession(
                user_id=self.user_id,
                connection_id=gh.item.id,
                request_id=body.request_id,
                repository=f"{body.owner}/{body.repo}",
                installation_id=body.installation_id,
                base_sha=sha,
                context={
                    "input": body.model_dump(mode="json"),
                    "files": files,
                    "evidence": evidence,
                },
                expires_at=datetime.now(UTC) + timedelta(hours=24),
            )
            self.db.add(row)
            self.db.flush()
            self.audit(row, "repository_authorized")
            self.audit(row, "snapshot_created")
            self.db.commit()
            return self.view(row)

    def clean_metadata(self, value):
        secrets = [self.gh().token]
        return redact_logs(value.encode(), False, secrets)[0][:2000]

    def generate(self, identity, body):
        with serialized(self.engine, self.user_id):
            self.budget()
            row = self.owned(identity)
            self.authorize(row)
            previous = self.db.scalar(
                select(AutomationProposal).where(
                    AutomationProposal.session_id == row.id,
                    AutomationProposal.request_id == body.request_id,
                )
            )
            if previous:
                if (
                    previous.content["request"] != body.request
                    or previous.content["mode"] != body.mode
                ):
                    raise reject(
                        "Proposal request identifier is already used by another request.", 409
                    )
                return self.view(row)
            count = self.db.scalar(
                select(func.count())
                .select_from(AutomationProposal)
                .where(AutomationProposal.session_id == row.id)
            )
            if count >= 5:
                raise reject("Five proposals per session allowed. Create a new session.", 429)
            try:
                self.clean_text(body.request)
                result = build_graph(self.ollama, self.clean_text).invoke(
                    {
                        "request": body.request,
                        "mode": body.mode,
                        "files": row.context["files"],
                        "evidence": row.context["evidence"],
                    },
                    {"recursion_limit": 4},
                )
                changes = result["validated"]
                content = {
                    "request": body.request,
                    "mode": body.mode,
                    "suggestion": result["suggestion"].model_dump(mode="json"),
                    "changes": changes,
                    "diff": "".join(c["diff"] for c in changes),
                }
                patch_hash = self.content_hash(row, content)
                item = AutomationProposal(
                    request_id=body.request_id,
                    session_id=row.id,
                    status="awaiting_approval" if changes else "explained",
                    patch_hash=patch_hash,
                    content=content,
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                )
                self.db.add(item)
                self.audit(row, "proposal_created" if changes else "explanation_created")
                self.db.commit()
            except AIError as exc:
                logging.getLogger("codemate.automation").warning(
                    "automation_generation_failed code=%s status=%s",
                    exc.detail["code"],
                    exc.status_code,
                )
                self.db.rollback()
                self.audit(row, "proposal_failed_or_policy_rejected")
                self.db.commit()
                raise
            return self.view(row)

    def content_hash(self, row, content):
        return digest(
            json.dumps(
                {
                    "user": str(self.user_id),
                    "workspace": str(row.workspace_id),
                    "repository": row.repository,
                    "connection": str(row.connection_id),
                    "base": row.base_sha,
                    "content": content,
                },
                sort_keys=True,
                separators=(",", ":"),
            )
        )

    def decide(self, identity, proposal_id, body):
        with serialized(self.engine, self.user_id):
            self.budget()
            row = self.owned(identity)
            self.authorize(row)
            item = self.db.scalar(
                select(AutomationProposal)
                .where(
                    AutomationProposal.id == proposal_id, AutomationProposal.session_id == row.id
                )
                .with_for_update()
            )
            try:
                if item is None:
                    raise reject("Proposal is unavailable.", 404)
                if item.status != "awaiting_approval" or item.expires_at <= datetime.now(UTC):
                    raise reject("Proposal already used or expired. Prepare a new proposal.", 409)
                if (
                    body.workspace_id != row.workspace_id
                    or body.base_sha != row.base_sha
                    or body.patch_hash != item.patch_hash
                    or self.content_hash(row, item.content) != item.patch_hash
                ):
                    raise reject(
                        "Workspace, revision or patch changed. Review a new proposal.", 409
                    )
                if len(set(body.validations)) != len(body.validations) or not set(
                    body.validations
                ) <= set(item.content["suggestion"]["validations"]):
                    raise reject("Select only the displayed backend-defined validation targets.")
                item.status = {"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[
                    body.decision
                ]
                item.approval = {
                    "user_id": str(self.user_id),
                    "workspace_id": str(row.workspace_id),
                    "repository": row.repository,
                    "base_sha": row.base_sha,
                    "patch_hash": item.patch_hash,
                    "action": "review_patch_only",
                    "decision": body.decision,
                    "validations": body.validations,
                    "at": datetime.now(UTC).isoformat(),
                    "expires_at": min(
                        item.expires_at, datetime.now(UTC) + timedelta(minutes=5)
                    ).isoformat(),
                }
                self.audit(row, "proposal_" + item.status)
                self.db.commit()
            except AIError:
                self.db.rollback()
                self.audit(row, "decision_policy_rejected")
                self.db.commit()
                raise
            return self.view(row)

    def execution_disabled(self, identity):
        row = self.owned(identity)
        self.authorize(row)
        self.audit(row, "execution_denied_no_sandbox")
        self.db.commit()
        raise AIError("AUTOMATION_EXECUTION_DISABLED", EXECUTION_MESSAGE, 503)

    def view(self, row):
        proposals = self.db.scalars(
            select(AutomationProposal)
            .where(AutomationProposal.session_id == row.id)
            .order_by(AutomationProposal.created_at)
        ).all()
        events = self.db.scalars(
            select(AutomationAudit)
            .where(AutomationAudit.session_id == row.id)
            .order_by(AutomationAudit.created_at.desc())
            .limit(50)
        ).all()
        return SessionView(
            id=row.id,
            workspace_id=row.workspace_id,
            repository=row.repository,
            base_sha=row.base_sha,
            expires_at=row.expires_at,
            files=list(row.context["files"]),
            evidence=row.context["evidence"],
            proposals=[
                Proposal(
                    id=p.id,
                    status=(
                        "expired"
                        if p.status == "awaiting_approval" and p.expires_at <= datetime.now(UTC)
                        else p.status
                    ),
                    request=p.content["request"],
                    mode=p.content["mode"],
                    patch_hash=p.patch_hash,
                    diff=p.content["diff"],
                    files=[c["path"] for c in p.content["changes"]],
                    suggestion=p.content["suggestion"],
                    expires_at=p.expires_at,
                    selected_validations=(p.approval or {}).get("validations", []),
                )
                for p in proposals
            ],
            audit=[{"event": e.event, "at": e.created_at.isoformat()} for e in events],
            execution_message=EXECUTION_MESSAGE,
        )

    def get(self, identity):
        row = self.owned(identity)
        self.authorize(row)
        return self.view(row)

    def history(self):
        rows = self.db.scalars(
            select(AutomationSession)
            .where(
                AutomationSession.user_id == self.user_id,
                AutomationSession.expires_at > datetime.now(UTC),
            )
            .order_by(AutomationSession.created_at.desc())
            .limit(10)
        ).all()
        return [
            {
                "id": str(r.id),
                "repository": r.repository,
                "base_sha": r.base_sha,
                "expires_at": r.expires_at.isoformat(),
            }
            for r in rows
        ]
