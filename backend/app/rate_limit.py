"""In-process, per-user sliding-window rate limiting (plan.md §21:
"Rate-limited auth, planning, and run start" — see
specs/phase-5-hardening.md FR-9/FR-10 for which routes and limits, and
Non-goals for why this is single-process, not distributed).
"""

import time
from collections import defaultdict
from typing import Annotated

from fastapi import Depends, HTTPException

from app.deps import CurrentUser, get_current_user

_WINDOWS: dict[tuple[str, str], list[float]] = defaultdict(list)


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded; retry after {retry_after:.1f}s")


def check_rate_limit(*, key: str, bucket: str, max_requests: int, window_seconds: float) -> None:
    """Raises RateLimitExceeded if `key` has already made `max_requests`
    calls to `bucket` within the trailing `window_seconds`; otherwise
    records this call. Pure in-memory state — see module docstring.
    """
    now = time.monotonic()
    window_key = (key, bucket)
    timestamps = _WINDOWS[window_key]

    cutoff = now - window_seconds
    while timestamps and timestamps[0] < cutoff:
        timestamps.pop(0)

    if len(timestamps) >= max_requests:
        retry_after = window_seconds - (now - timestamps[0])
        raise RateLimitExceeded(retry_after=max(retry_after, 0.0))

    timestamps.append(now)


def reset() -> None:
    """Clears all rate-limit state — used by an autouse test fixture so one
    test's requests never affect another's (tests/conftest.py).
    """
    _WINDOWS.clear()


def rate_limiter(bucket: str, max_requests: int, window_seconds: float):
    """Returns a FastAPI dependency suitable for a route's `dependencies=`
    list (side-effect-only — it injects nothing into the handler).
    """

    async def _check(current_user: Annotated[CurrentUser, Depends(get_current_user)]) -> None:
        try:
            check_rate_limit(
                key=current_user.id,
                bucket=bucket,
                max_requests=max_requests,
                window_seconds=window_seconds,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(
                status_code=429,
                detail={
                    "code": "rate_limited",
                    "message": "Too many requests. Please slow down and try again shortly.",
                    "details": {"retry_after_seconds": round(exc.retry_after, 1)},
                },
            ) from exc

    return _check
