import json
import logging
import time
from datetime import UTC, datetime

from sqlalchemy import select, text

from app.ai.errors import AIError
from app.ai.graph import build_graph
from app.ai.schemas import Report
from app.core.observability import correlation
from app.integrations.github.authorization_cache import AuthorizationCache
from app.integrations.github.exceptions import GitHubError
from app.models import AIInvestigation, User
from app.services.ai_investigation_service import purge_expired
from app.services.github_repository_service import GitHubRepositoryService

logger = logging.getLogger("codemate.ai")


class InvestigationWorker:
    """Durable queue with session advisory locks; no API fire-and-forget tasks."""

    def __init__(self, settings, factory, engine, github_client, ollama):
        self.settings, self.factory, self.engine = settings, factory, engine
        self.github_client, self.ollama = github_client, ollama

    def tick(self) -> bool:
        with self.engine.connect() as guard:
            slot = None
            job_lock = None
            user_lock = None
            try:
                for number in range(self.settings.ai_max_concurrent_investigations):
                    if guard.scalar(
                        text("SELECT pg_try_advisory_lock(51805,:slot)"), {"slot": number}
                    ):
                        slot = number
                        break
                guard.commit()
                if slot is None:
                    return False
                with self.factory() as db:
                    purge_expired(db, self.settings)
                    candidates = list(
                        db.scalars(
                            select(AIInvestigation)
                            .where(AIInvestigation.status.in_(("queued", "running")))
                            .order_by(AIInvestigation.created_at)
                            .limit(50)
                        )
                    )
                    for item in candidates:
                        user_key = int.from_bytes(item.user_id.bytes[:4], "big", signed=True)
                        if not guard.scalar(
                            text("SELECT pg_try_advisory_lock(51806,:key)"), {"key": user_key}
                        ):
                            continue
                        user_lock = user_key
                        key = int.from_bytes(item.id.bytes[:8], "big", signed=True)
                        if not guard.scalar(
                            text("SELECT pg_try_advisory_lock(:key)"), {"key": key}
                        ):
                            guard.execute(
                                text("SELECT pg_advisory_unlock(51806,:key)"), {"key": user_key}
                            )
                            user_lock = None
                            continue
                        guard.commit()
                        job_lock = key
                        db.expire_all()
                        identity = item.id
                        item = db.scalar(
                            select(AIInvestigation)
                            .where(AIInvestigation.id == identity)
                            .with_for_update()
                        )
                        if not item or item.status not in {"queued", "running"}:
                            break
                        if item.attempts >= self.settings.ai_max_retries + 1:
                            item.status, item.stage = "failed", "failed"
                            item.error_code = "AI_RETRY_LIMIT"
                            item.error_message = (
                                "Interrupted execution exhausted the attempt limit."
                            )
                            item.completed_at = datetime.now(UTC)
                            db.commit()
                            return True
                        item.attempts += 1
                        item.status, item.stage = "running", "starting"
                        item.started_at = datetime.now(UTC)
                        item.completed_at = None
                        db.commit()
                        correlation_token = correlation.set({"correlation_id": str(identity)})
                        try:
                            self.execute(db, item)
                        finally:
                            correlation.reset(correlation_token)
                        return True
                return False
            finally:
                if job_lock is not None:
                    guard.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": job_lock})
                if user_lock is not None:
                    guard.execute(text("SELECT pg_advisory_unlock(51806,:key)"), {"key": user_lock})
                if slot is not None:
                    guard.execute(text("SELECT pg_advisory_unlock(51805,:slot)"), {"slot": slot})
                guard.commit()

    def execute(self, db, item):
        started = time.monotonic()
        deadline = started + self.settings.ai_investigation_timeout_seconds
        identity = item.id
        attempt = item.attempts

        def check():
            db.expire_all()
            current = db.get(AIInvestigation, identity)
            if current is None or current.status == "cancelled":
                raise AIError("AI_CANCELLED", "Investigation cancelled.", 409)
            user = db.get(User, current.user_id)
            if user is None or not user.is_active:
                raise AIError("AI_UNAUTHORIZED", "Account is unavailable.", 403)
            if time.monotonic() > deadline:
                raise AIError("AI_TIMEOUT", "Investigation exceeded its deadline.")

        def stage(name):
            item.stage = name
            db.commit()
            logger.info(
                json.dumps(
                    {
                        "event": "ai_stage",
                        "investigation_id": str(identity),
                        "stage": name,
                        "attempt": attempt,
                    }
                )
            )

        try:
            check()
            github = GitHubRepositoryService(
                db, self.settings, self.github_client, AuthorizationCache(), item.user_id
            )
            context = {
                "owner": item.owner,
                "repo": item.repo,
                "installation_id": item.installation_id,
                "connection_id": str(item.github_connection_id),
                "run_id": item.workflow_run_id,
                "deadline": deadline,
            }
            graph = build_graph(self.settings, github, self.ollama, context, check, stage)
            result = graph.invoke(
                {
                    "user_id": str(item.user_id),
                    "connection_id": str(item.github_connection_id),
                    "run_id": item.workflow_run_id,
                    "attempt": attempt,
                },
                {"recursion_limit": 12, "callbacks": []},
            )
            check()
            report = Report.model_validate(result["report"]).model_dump(mode="json")
            if len(json.dumps(report).encode()) > 128 * 1024:
                raise AIError("AI_INVALID_OUTPUT", "Report exceeds the safe storage limit.", 502)
            current = db.scalar(
                select(AIInvestigation)
                .where(AIInvestigation.id == identity)
                .with_for_update()
                .execution_options(populate_existing=True)
            )
            if current is None or current.status == "cancelled":
                raise AIError("AI_CANCELLED", "Investigation cancelled.", 409)
            item.report = report
            item.model_name = report["model_name"]
            item.status, item.stage = "completed", "completed"
            item.completed_at = datetime.now(UTC)
            db.commit()
        except Exception as exc:
            db.rollback()
            current = db.get(AIInvestigation, identity)
            if current is not None and current.status != "cancelled":
                current.status, current.stage = "failed", "failed"
                safe = isinstance(exc, (AIError, GitHubError))
                current.error_code = exc.detail["code"] if safe else "AI_INTERNAL_ERROR"
                current.error_message = (
                    exc.detail["message"]
                    if safe
                    else "Investigation failed safely. Retry within the attempt limit."
                )
                current.completed_at = datetime.now(UTC)
                db.commit()
        finally:
            logger.info(
                json.dumps(
                    {
                        "event": "ai_finished",
                        "investigation_id": str(identity),
                        "duration_ms": int((time.monotonic() - started) * 1000),
                        "attempt": attempt,
                    }
                )
            )
