import json
import logging
import os
import time
from collections.abc import Callable
from typing import TypedDict

os.environ["LANGSMITH_TRACING"] = "false"
os.environ["LANGCHAIN_TRACING_V2"] = "false"
from langgraph.graph import END, START, StateGraph

from app.ai.errors import AIError, invalid_output
from app.ai.evidence import extract
from app.ai.schemas import Diagnosis, Evidence, Report, ground
from app.core.config import Settings
from app.integrations.github.exceptions import GitHubError
from app.integrations.github.logs import redact_logs
from app.integrations.github.schemas import Job, Run
from app.integrations.ollama.client import OllamaClient
from app.services.github_repository_service import GitHubRepositoryService


class InvestigationState(TypedDict, total=False):
    user_id: str
    connection_id: str
    repository_id: int
    run_id: int
    attempt: int
    run: Run
    jobs: list[Job]
    evidence: list[Evidence]
    signals: list[str]
    errors: list[str]
    completeness: str
    diagnosis: Diagnosis
    report: Report
    execution_state: str


def build_graph(
    settings: Settings,
    github: GitHubRepositoryService,
    ollama: OllamaClient,
    context: dict,
    check: Callable[[], None],
    stage: Callable[[str], None],
):
    def node(name, function):
        def execute(state):
            check()
            stage(name)
            started = time.monotonic()
            try:
                update = function(state)
            finally:
                logging.getLogger("codemate.ai").info(
                    json.dumps(
                        {
                            "event": "ai_node_finished",
                            "node": name,
                            "duration_ms": int((time.monotonic() - started) * 1000),
                            "attempt": state.get("attempt", 0),
                        }
                    )
                )
            check()
            return {**update, "execution_state": name}

        return execute

    def authorize(state):
        repo = github.repository(context["owner"], context["repo"], context["installation_id"])
        if str(github.item.id) != context["connection_id"]:
            raise AIError(
                "AI_CONNECTION_CHANGED", "The original GitHub connection is unavailable.", 409
            )
        return {"repository_id": repo.id}

    def fetch_run(state):
        run = github.run(
            context["owner"], context["repo"], context["installation_id"], context["run_id"]
        )
        if run.status != "completed":
            raise AIError("AI_RUN_NOT_COMPLETED", "The run is no longer completed.", 422)
        return {"run": run}

    def jobs(state):
        page = github.resource(
            context["owner"],
            context["repo"],
            context["installation_id"],
            "jobs",
            1,
            settings.ai_max_jobs,
            run_id=context["run_id"],
        )
        ordered = sorted(
            page.items[: settings.ai_max_jobs],
            key=lambda j: j.conclusion not in {"failure", "timed_out", "cancelled"},
        )
        return {
            "jobs": ordered,
            "completeness": "partial"
            if page.has_next or len(page.items) > settings.ai_max_jobs
            else "complete",
            "errors": [],
        }

    def logs(state):
        evidence, errors = [], []
        if state["run"].conclusion == "success":
            metadata = json.dumps(
                {
                    "run_id": context["run_id"],
                    "run_conclusion": "success",
                    "jobs": [{"id": job.id, "conclusion": job.conclusion} for job in state["jobs"]],
                }
            )
            return {
                "evidence": [
                    Evidence(
                        id=f"R-{context['run_id']}",
                        workflow_run_id=context["run_id"],
                        job_id=None,
                        step=None,
                        source="run_metadata",
                        excerpt=metadata[:4000],
                    )
                ]
            }
        for job in state["jobs"]:
            check()
            if job.conclusion == "success":
                continue
            failing = next((step.name for step in job.steps if step.conclusion == "failure"), None)
            metadata = json.dumps(
                {
                    "job": job.name[:200],
                    "status": job.status,
                    "conclusion": job.conclusion,
                    "failed_step": failing,
                },
                ensure_ascii=False,
            )
            remaining = settings.ai_max_evidence_chars - sum(len(e.excerpt) for e in evidence)
            if remaining <= 0:
                errors.append("Evidence budget reached; some job logs were omitted.")
                break
            metadata, _, _ = redact_logs(metadata.encode(), False, [github.token])
            evidence.append(
                Evidence(
                    id=f"M-{job.id}",
                    workflow_run_id=context["run_id"],
                    job_id=job.id,
                    step=failing,
                    source="job_metadata",
                    excerpt=metadata[: min(2000, remaining)],
                )
            )
            used = sum(len(item.excerpt) for item in evidence)
            budget = min(settings.ai_per_job_chars, max(0, settings.ai_max_evidence_chars - used))
            if not budget:
                errors.append("Evidence budget reached; some job logs were omitted.")
                break
            try:
                result = github.logs(
                    context["owner"], context["repo"], context["installation_id"], job.id
                )
                evidence.extend(
                    extract(
                        result["content"],
                        context["run_id"],
                        job.id,
                        failing,
                        budget,
                        settings.ai_max_log_chars,
                        result["truncated"],
                    )
                )
            except GitHubError as exc:
                if exc.detail["code"] not in {
                    "GITHUB_LOGS_UNAVAILABLE",
                    "GITHUB_RESOURCE_UNAVAILABLE",
                    "GITHUB_UNAVAILABLE",
                    "GITHUB_TIMEOUT",
                }:
                    raise
                errors.append(
                    "Job logs were unavailable; metadata alone cannot establish the root cause."
                )
        return {
            "evidence": evidence[:24],
            "errors": errors[:5],
            "completeness": "partial"
            if errors or any(e.truncated for e in evidence)
            else state["completeness"],
        }

    def signals(state):
        return {
            "signals": [e.id for e in state["evidence"] if e.source == "job_log"],
            "completeness": state["completeness"] if state["evidence"] else "missing",
        }

    def diagnose(state):
        if state["run"].conclusion == "success":
            result = Diagnosis(
                summary="No CI failure detected. GitHub reports this completed run succeeded.",
                failure_category="no_failure",
                findings=[],
                recommended_actions=[],
                limitations=[
                    "This is a verified metadata summary; no model inference was performed."
                ],
            )
        elif not state["signals"]:
            result = Diagnosis(
                summary=(
                    "The run did not succeed, but log evidence is insufficient "
                    "to diagnose its cause."
                ),
                failure_category="unknown",
                findings=[],
                recommended_actions=["Review job logs on GitHub."],
                limitations=["Missing log evidence. Root cause is uncertain."],
            )
        else:
            payload = {
                "run_conclusion": state["run"].conclusion,
                "evidence": [e.model_dump() for e in state["evidence"]],
            }
            result = ollama.diagnose(
                payload,
                check,
                min(
                    settings.ollama_timeout_seconds, max(1, context["deadline"] - time.monotonic())
                ),
            )
        return {"diagnosis": result}

    def validate(state):
        try:
            result = ground(state["diagnosis"], state["evidence"])
        except ValueError as exc:
            raise invalid_output() from exc
        if state["run"].conclusion != "success" and result.failure_category == "no_failure":
            raise invalid_output()
        return {"diagnosis": result}

    def report(state):
        run = state["run"]
        result = state["diagnosis"]
        value = Report(
            **{
                **result.model_dump(),
                "limitations": list(
                    dict.fromkeys(
                        result.limitations
                        + state["errors"]
                        + ["Hypotheses and suggestions are unverified. No changes were applied."]
                    )
                )[:10],
            },
            workflow_name=run.name,
            commit_sha=run.sha,
            branch=run.branch,
            run_conclusion=run.conclusion,
            analyzed_job_ids=[j.id for j in state["jobs"]],
            model_name=settings.ollama_model
            if state["signals"] and run.conclusion != "success"
            else None,
            evidence_completeness=state["completeness"],
            evidence=state["evidence"],
        )
        return {"report": value}

    graph = StateGraph(InvestigationState)
    steps = [
        ("authorize", authorize),
        ("fetch_run", fetch_run),
        ("fetch_jobs", jobs),
        ("collect_evidence", logs),
        ("extract_signals", signals),
        ("local_diagnosis", diagnose),
        ("ground_findings", validate),
        ("build_report", report),
    ]
    previous = START
    for name, function in steps:
        graph.add_node(name, node(name, function))
        graph.add_edge(previous, name)
        previous = name
    graph.add_edge(previous, END)
    return graph.compile()
