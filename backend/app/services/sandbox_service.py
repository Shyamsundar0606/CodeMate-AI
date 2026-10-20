"""Durable safe previews. This module cannot materialize or execute repository code."""

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.ai.errors import AIError
from app.automation.policy import patch, reject
from app.automation.schemas import Suggestion
from app.models.automation import AutomationProposal
from app.models.sandbox import SandboxAudit, SandboxPreview
from app.sandbox.policy import ISOLATION, PROFILE, capabilities, fingerprint
from app.services.voice_service import serialized


class SandboxService:
    def __init__(self, automation):
        self.automation = automation
        self.db = automation.db
        self.owner = automation.user_id

    def audit(self, row, event):
        # Repeated denied confirmations must not grow durable audit storage without bound.
        if self.db.scalar(
            select(SandboxAudit.id).where(
                SandboxAudit.preview_id == row.id,
                SandboxAudit.event == event,
            )
        ):
            return
        self.db.add(SandboxAudit(preview_id=row.id, event=event))

    def proposal(self, session_id, proposal_id):
        session = self.automation.owned(session_id)
        self.automation.authorize(session)
        proposal = self.db.scalar(
            select(AutomationProposal)
            .where(
                AutomationProposal.id == proposal_id,
                AutomationProposal.session_id == session.id,
            )
            .with_for_update()
        )
        if (
            not proposal
            or proposal.status != "approved"
            or proposal.expires_at <= datetime.now(UTC)
        ):
            raise reject("A current approved patch proposal is required.", 409)
        approval = proposal.approval or {}
        expected = {
            "user_id": str(self.owner),
            "workspace_id": str(session.workspace_id),
            "repository": session.repository,
            "base_sha": session.base_sha,
            "patch_hash": proposal.patch_hash,
            "action": "review_patch_only",
            "decision": "approve",
        }
        if any(approval.get(k) != v for k, v in expected.items()):
            raise reject("Review approval binding changed. Review a new proposal.", 409)
        if self.automation.content_hash(session, proposal.content) != proposal.patch_hash:
            raise reject("Patch content hash changed.", 409)
        suggestion = Suggestion.model_validate(proposal.content["suggestion"])
        changes = patch(session.context["files"], suggestion.changes)
        if (
            not changes
            or changes != proposal.content["changes"]
            or "".join(c["diff"] for c in changes) != proposal.content["diff"]
        ):
            raise reject("Patch artifacts do not match the validated replacements.", 409)
        if any(not c["path"].endswith(".py") for c in changes):
            raise reject("The initial syntax profile supports Python changes only.")
        return session, proposal, changes

    def prepare(self, body):
        with serialized(self.automation.engine, self.owner):
            session, proposal, changes = self.proposal(body.session_id, body.proposal_id)
            existing = self.db.scalar(
                select(SandboxPreview).where(
                    SandboxPreview.user_id == self.owner,
                    SandboxPreview.request_id == body.request_id,
                )
            )
            request = body.model_dump(mode="json")
            if existing:
                if existing.preview["request"] != request:
                    raise reject("Request identifier already binds another preview.", 409)
                self.authorize_preview(existing)
                return self.view(existing)
            count = self.db.scalar(
                select(func.count())
                .select_from(SandboxPreview)
                .where(
                    SandboxPreview.user_id == self.owner,
                )
            )
            if count >= 100:
                raise reject("Preview history limit reached (100 per account).", 429)
            expiry = min(
                session.expires_at, proposal.expires_at, datetime.now(UTC) + timedelta(minutes=5)
            )
            identity = uuid.uuid4()
            preview = {
                "request": request,
                "execution_id": str(identity),
                "user_id": str(self.owner),
                "repository": session.repository,
                "installation_id": session.installation_id,
                "connection_id": str(session.connection_id),
                "base_sha": session.base_sha,
                "proposal_id": str(proposal.id),
                "patch_hash": proposal.patch_hash,
                "files": [c["path"] for c in changes],
                "diff": proposal.content["diff"],
                "expected_manifest": [
                    {k: c[k] for k in ("path", "before_sha256", "after_sha256")} for c in changes
                ],
                "profiles": [PROFILE],
                "isolation": ISOLATION,
                "expires_at": expiry.isoformat(),
            }
            row = SandboxPreview(
                id=identity,
                user_id=self.owner,
                request_id=body.request_id,
                proposal_id=proposal.id,
                preview=preview,
                binding_hash=fingerprint(preview),
                expires_at=expiry,
            )
            self.db.add(row)
            self.db.flush()
            for event in (
                "proposal_authorization_checked",
                "sandbox_capability_checked",
                "execution_preview_prepared",
            ):
                self.audit(row, event)
            self.db.commit()
            return self.view(row)

    def owned(self, identity):
        row = self.db.scalar(
            select(SandboxPreview)
            .where(
                SandboxPreview.id == identity,
                SandboxPreview.user_id == self.owner,
            )
            .with_for_update()
        )
        if row is None:
            raise reject("Execution preview unavailable.", 404)
        if row.state == "awaiting_confirmation" and row.expires_at <= datetime.now(UTC):
            row.state = "expired"
            self.audit(row, "execution_preview_expired")
            self.db.commit()
        return row

    def authorize_preview(self, row):
        if fingerprint(row.preview) != row.binding_hash:
            raise reject("Stored preview integrity check failed.", 409)
        gh = self.automation.gh()
        if str(gh.item.id) != row.preview["connection_id"]:
            raise reject("GitHub connection changed. Prepare a new preview.", 409)
        owner, repo = row.preview["repository"].split("/")
        gh.repository(owner, repo, row.preview["installation_id"])

    def get(self, identity):
        row = self.owned(identity)
        self.authorize_preview(row)
        return self.view(row)

    def history(self):
        rows = self.db.scalars(
            select(SandboxPreview)
            .where(
                SandboxPreview.user_id == self.owner,
            )
            .order_by(SandboxPreview.created_at.desc())
            .limit(50)
        ).all()
        for row in rows:
            self.authorize_preview(row)
        return [self.view(row) for row in rows]

    def cancel(self, identity):
        with serialized(self.automation.engine, self.owner):
            row = self.owned(identity)
            self.authorize_preview(row)
            if row.state == "awaiting_confirmation":
                row.state = "cancelled"
                self.audit(row, "execution_preview_cancelled")
                self.db.commit()
            return self.view(row)

    def confirm(self, identity, body):
        with serialized(self.automation.engine, self.owner):
            row = self.owned(identity)
            self.authorize_preview(row)
            if row.state != "awaiting_confirmation":
                raise reject("Execution preview was cancelled or expired.", 409)
            request = row.preview["request"]
            source, proposal, changes = self.proposal(
                uuid.UUID(request["session_id"]), uuid.UUID(request["proposal_id"])
            )
            if (
                source.base_sha != row.preview["base_sha"]
                or proposal.patch_hash != row.preview["patch_hash"]
                or proposal.content["diff"] != row.preview["diff"]
            ):
                raise reject(
                    "Source revision or approved patch changed. Prepare a new preview.", 409
                )
            if (
                body.binding_hash != row.binding_hash
                or fingerprint(row.preview) != row.binding_hash
                or row.preview["isolation"] != ISOLATION
                or row.preview["profiles"] != [PROFILE]
            ):
                self.audit(row, "confirmation_binding_rejected")
                self.db.commit()
                raise reject("Execution preview changed. Prepare a new preview.", 409)
            self.audit(row, "confirmation_denied_sandbox_unverified")
            self.db.commit()
            raise AIError("SANDBOX_UNVERIFIED", capabilities()["reasons"][0], 503)

    def view(self, row):
        events = self.db.scalars(
            select(SandboxAudit)
            .where(
                SandboxAudit.preview_id == row.id,
            )
            .order_by(SandboxAudit.created_at.desc(), SandboxAudit.id)
            .limit(50)
        ).all()
        state = row.state
        if state == "awaiting_confirmation" and row.expires_at <= datetime.now(UTC):
            state = "expired"
        return {
            "id": str(row.id),
            "state": state,
            "binding_hash": row.binding_hash,
            "preview": row.preview,
            "expires_at": row.expires_at.isoformat(),
            "execution_enabled": False,
            "applied": False,
            "validation_status": "not_executed",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "changed_manifest": [],
            "audit": [{"event": e.event, "at": e.created_at.isoformat()} for e in events],
        }
