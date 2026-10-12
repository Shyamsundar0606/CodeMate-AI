import hashlib
import re

from app.ai.schemas import Evidence
from app.integrations.github.logs import redact_logs

SIGNAL = re.compile(
    r"error|failed|exception|traceback|assertion|module.?not.?found|importerror|npm ERR|"
    r"TS[0-9]{4}|eslint|connection.*(?:refused|failed)|migration|permission denied|"
    r"timeout|timed out|exited with code|out of memory|OOM|killed",
    re.I,
)


def extract(
    raw: str,
    run_id: int,
    job_id: int,
    step: str | None,
    budget: int,
    log_limit: int,
    upstream_truncated: bool = False,
) -> list[Evidence]:
    content, truncated, _ = redact_logs(
        raw.encode("utf-8")[: log_limit * 4], upstream_truncated, []
    )
    truncated = truncated or len(content) > log_limit
    lines = content[:log_limit].splitlines()
    found = [i for i, line in enumerate(lines) if SIGNAL.search(line)]
    if not found and lines:
        found = [max(0, len(lines) - 3)]
    result = []
    used = 0
    seen = set()
    covered = -1
    for index in found:
        if index <= covered or len(result) >= 6 or used >= budget:
            continue
        start, end = max(0, index - 2), min(len(lines), index + 4)
        excerpt = "\n".join(lines[start:end])[: min(4000, budget - used)]
        fingerprint = hashlib.sha256(excerpt.encode()).hexdigest()
        if fingerprint in seen or not excerpt:
            continue
        seen.add(fingerprint)
        used += len(excerpt)
        covered = end - 1
        identity = hashlib.sha256(f"{run_id}/{job_id}/{start}/{excerpt}".encode()).hexdigest()[:16]
        result.append(
            Evidence(
                id="E-" + identity,
                workflow_run_id=run_id,
                job_id=job_id,
                step=step,
                source="job_log",
                excerpt=excerpt,
                line_start=start + 1,
                line_end=end,
                truncated=truncated or used >= budget,
            )
        )
    return result
