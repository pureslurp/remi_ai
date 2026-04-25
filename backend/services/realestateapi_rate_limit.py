"""Simple in-memory per-account rate limits for RealEstateAPI BFF routes."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import HTTPException

# Window and max requests per account (rolling).
_WINDOW_SEC = 60.0
_MAX_PER_WINDOW = 40

_ts: dict[str, Deque[float]] = defaultdict(deque)
_guard = threading.Lock()


def check_rate_limit(account_id: str) -> None:
    """Raises HTTP 429 if account_id exceeded the per-minute cap."""
    if not account_id:
        return
    now = time.monotonic()
    key = str(account_id)
    with _guard:
        q = _ts[key]
        while q and now - q[0] > _WINDOW_SEC:
            q.popleft()
        if len(q) >= _MAX_PER_WINDOW:
            raise HTTPException(
                status_code=429,
                detail="Too many property-data requests. Try again in a minute.",
            )
        q.append(now)
