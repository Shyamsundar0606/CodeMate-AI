import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.ai.errors import AIError
from app.ai.schemas import History, InvestigationRequest, InvestigationResponse
from app.core.config import Settings
from app.integrations.github.schemas import valid_repository_path
from app.models import AIInvestigation, User
from app.services.github_repository_service import GitHubRepositoryService

ACTIVE = ("queued", "running")


class InvestigationService:
    def __init__(
        self,
        db: Session,
        settings: Settings,
        user_id: uuid.UUID,
        github: GitHubRepositoryService | None = None,
    ):
        self.db, self.settings, self.user_id, self.github = db, settings, user_id, github

    def owned(self, investigation_id: uuid.UUID, lock: bool = False) -> AIInvestigation:
        query = select(AIInvestigation).where(
            AIInvestigation.id == investigation_id, AIInvestigation.user_id == self.user_id
        )
        if lock:
            query = query.with_for_update()
        item = self.db.scalar(query)
        if item is None:
            raise AIError("AI_NOT_FOUND", "Investigation not found.", 404)
        return item

    def response(self, item: AIInvestigation) -> InvestigationResponse:
        return InvestigationResponse(
            id=item.id,
            owner=item.owner,
            repo=item.repo,
            workflow_run_id=item.workflow_run_id,
            installation_id=item.installation_id,
            status=item.status,
            stage=item.stage,
            attempts=item.attempts,
            max_attempts=self.settings.ai_max_retries + 1,
            created_at=item.created_at,
            started_at=item.started_at,
            completed_at=item.completed_at,
            error_code=item.error_code,
            error_message=item.error_message,
            report=item.report,
        )

    def admit(self):
        self.db.scalar(select(User).where(User.id == self.user_id).with_for_update())
        count = self.db.scalar(
            select(func.count())
            .select_from(AIInvestigation)
            .where(AIInvestigation.user_id == self.user_id, AIInvestigation.status.in_(ACTIVE))
        )
        if count:
            raise AIError(
                "AI_USER_BUSY",
                "An investigation is already queued or running for this account.",
                409,
            )

    def create(self, request: InvestigationRequest):
        valid_repository_path(request.owner, request.repo)
        run = self.github.run(
            request.owner, request.repo, request.installation_id, request.workflow_run_id
        )
        if run.status != "completed":
            raise AIError("AI_RUN_NOT_COMPLETED", "Select a completed workflow run.", 422)
        self.db.scalar(select(User).where(User.id == self.user_id).with_for_update())
        existing = self.db.scalar(
            select(AIInvestigation).where(
                AIInvestigation.user_id == self.user_id,
                AIInvestigation.github_connection_id == self.github.item.id,
                AIInvestigation.installation_id == request.installation_id,
                AIInvestigation.owner == request.owner,
                AIInvestigation.repo == request.repo,
                AIInvestigation.workflow_run_id == request.workflow_run_id,
            )
        )
        if existing:
            return self.response(existing)
        self.admit()
        item = AIInvestigation(
            user_id=self.user_id,
            github_connection_id=self.github.item.id,
            owner=request.owner,
            repo=request.repo,
            installation_id=request.installation_id,
            workflow_run_id=request.workflow_run_id,
        )
        self.db.add(item)
        self.db.commit()
        return self.response(item)

    def history(self, page: int, size: int) -> History:
        owned = AIInvestigation.user_id == self.user_id
        values = list(
            self.db.scalars(
                select(AIInvestigation)
                .where(owned)
                .order_by(AIInvestigation.created_at.desc(), AIInvestigation.id)
                .offset((page - 1) * size)
                .limit(size + 1)
            )
        )
        counts = dict(
            self.db.execute(
                select(AIInvestigation.status, func.count())
                .where(owned)
                .group_by(AIInvestigation.status)
            ).all()
        )
        return History(
            items=[self.response(item) for item in values[:size]],
            page=page,
            has_next=len(values) > size,
            completed_count=counts.get("completed", 0),
            failed_count=counts.get("failed", 0),
        )

    def retry(self, investigation_id: uuid.UUID):
        item = self.owned(investigation_id)
        if item.status != "failed" or item.attempts >= self.settings.ai_max_retries + 1:
            raise AIError(
                "AI_RETRY_LIMIT",
                "Only failed investigations within the attempt limit can retry.",
                409,
            )
        self.github.run(item.owner, item.repo, item.installation_id, item.workflow_run_id)
        if item.github_connection_id != self.github.item.id:
            raise AIError(
                "AI_CONNECTION_CHANGED",
                "The original GitHub connection is no longer available.",
                409,
            )
        self.admit()
        item = self.owned(investigation_id, True)
        if item.status != "failed" or item.attempts >= self.settings.ai_max_retries + 1:
            raise AIError("AI_RETRY_LIMIT", "Investigation state changed.", 409)
        item.status, item.stage = "queued", "queued"
        item.error_code = item.error_message = None
        item.report = None
        self.db.commit()
        return self.response(item)

    def cancel(self, investigation_id: uuid.UUID):
        item = self.owned(investigation_id, True)
        if item.status not in ACTIVE:
            raise AIError("AI_NOT_ACTIVE", "Only queued or running investigations can cancel.", 409)
        item.status, item.stage = "cancelled", "cancelled"
        item.completed_at = datetime.now(UTC)
        self.db.commit()
        return self.response(item)

    def remove(self, investigation_id: uuid.UUID):
        item = self.owned(investigation_id, True)
        if item.status in ACTIVE:
            raise AIError(
                "AI_NOT_ACTIVE", "Cancel the active investigation before deleting it.", 409
            )
        self.db.delete(item)
        self.db.commit()
        return {"deleted": True}


def purge_expired(db: Session, settings: Settings):
    cutoff = datetime.now(UTC) - timedelta(days=settings.ai_investigation_retention_days)
    db.execute(
        delete(AIInvestigation).where(
            AIInvestigation.status.not_in(ACTIVE), AIInvestigation.completed_at < cutoff
        )
    )
    db.commit()
