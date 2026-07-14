"""Exponential backoff retry utility (Day 48).

Wraps any callable with automatic retry on exception. A transient Kraken
API error or network blip should not abort a trading cycle — retry a few
times with increasing delays before giving up.

Usage (call wrapper):
    from retry import with_retry
    balance = with_retry(get_balance, client, max_attempts=3, base_delay=1.0)

Usage (decorator):
    from retry import retryable

    @retryable(max_attempts=3, base_delay=2.0)
    def fetch_data():
        ...

Delay schedule: base_delay * 2^attempt  (1s, 2s, 4s, ...)
Last exception is re-raised if all attempts are exhausted.
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def with_retry(
    fn: Callable[..., Any],
    *args: Any,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    **kwargs: Any,
) -> Any:
    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            if attempt < max_attempts - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    "%s failed (attempt %d/%d): %s — retrying in %.1fs",
                    getattr(fn, "__name__", str(fn)),
                    attempt + 1,
                    max_attempts,
                    exc,
                    delay,
                )
                time.sleep(delay)
            else:
                logger.error(
                    "%s failed after %d attempt(s): %s",
                    getattr(fn, "__name__", str(fn)),
                    max_attempts,
                    exc,
                )
    raise last_exc  # type: ignore[misc]


def retryable(max_attempts: int = 3, base_delay: float = 1.0) -> Callable[[F], F]:
    def decorator(fn: F) -> F:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            return with_retry(fn, *args, max_attempts=max_attempts, base_delay=base_delay, **kwargs)
        return wrapper  # type: ignore[return-value]
    return decorator
