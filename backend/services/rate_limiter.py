"""In-memory sliding-window rate limiter per spec §13.1.
Max 10 requests per player_id per 60 seconds on /api/dialogue."""

import time
from collections import defaultdict, deque
from threading import Lock

_WINDOW_SECONDS = 60
_MAX_REQUESTS = 10

_buckets: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def allow(player_id: str) -> bool:
    """Return True if the player is under the quota. Side effect: records the call."""
    now = time.monotonic()
    with _lock:
        bucket = _buckets[player_id]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= _MAX_REQUESTS:
            return False
        bucket.append(now)
        return True
