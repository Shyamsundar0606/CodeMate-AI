import threading
import time
from collections import OrderedDict

from app.integrations.github.exceptions import GitHubError


class RateLimitGuard:
    """Bounded, process-local backoff; no token or response bodies retained."""

    def __init__(self):
        self.lock = threading.Lock()
        self.entries: OrderedDict[str, tuple[float, int | None]] = OrderedDict()

    def check(self, key: str) -> None:
        with self.lock:
            value = self.entries.get(key)
            if value and value[0] > time.monotonic():
                raise GitHubError(
                    "GITHUB_RATE_LIMITED",
                    "GitHub rate limit reached. Wait before refreshing.",
                    429,
                    retry_after=max(1, int(value[0] - time.monotonic()) + 1),
                    reset_at=value[1],
                )
            self.entries.pop(key, None)

    def record(self, key: str, seconds: int, reset_at: int | None) -> None:
        with self.lock:
            self.entries[key] = (time.monotonic() + seconds, reset_at)
            self.entries.move_to_end(key)
            while len(self.entries) > 512:
                self.entries.popitem(last=False)
