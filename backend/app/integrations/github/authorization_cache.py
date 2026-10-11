import threading
import time
from collections import OrderedDict


class AuthorizationCache:
    """Only installation membership IDs; 15-second TTL, bounded and owner/token isolated."""

    def __init__(self):
        self.entries = OrderedDict()
        self.lock = threading.Lock()

    def put(self, key: tuple, repository_id: int) -> None:
        with self.lock:
            self.entries[key] = (time.monotonic() + 15, repository_id)
            self.entries.move_to_end(key)
            while len(self.entries) > 1024:
                self.entries.popitem(last=False)

    def get(self, key: tuple) -> int | None:
        with self.lock:
            value = self.entries.get(key)
            if value and value[0] > time.monotonic():
                return value[1]
            self.entries.pop(key, None)
            return None

    def clear_user(self, user_id: str) -> None:
        with self.lock:
            for key in list(self.entries):
                if key[0] == user_id:
                    self.entries.pop(key, None)
