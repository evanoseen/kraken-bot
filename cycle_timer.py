"""Cycle timing decorator (Day 50).

Wraps any function with a timer that logs elapsed seconds on completion.
Applied to run_trading_cycle() so every log shows how long the cycle took.

Usage:
    from cycle_timer import timed

    @timed
    def run_trading_cycle():
        ...
"""
from __future__ import annotations

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def timed(fn: Callable[..., Any]) -> Callable[..., Any]:
    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        try:
            return fn(*args, **kwargs)
        finally:
            elapsed = time.monotonic() - start
            logger.info("Cycle duration: %.2fs", elapsed)
    return wrapper
