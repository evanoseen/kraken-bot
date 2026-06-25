"""Per-coin trade cooldown tracker (Day 29).

After a trade fires on a coin, that coin is blocked for TRADE_COOLDOWN_MINUTES.
State lives in-process (dict reset on restart) — intentional, so a bot restart
clears all cooldowns and lets the next cycle trade fresh.

Usage:
    from cooldown import mark_traded, is_on_cooldown
    mark_traded("DOGE")
    is_on_cooldown("DOGE")  # True for the next N minutes
"""
from __future__ import annotations

import time
from typing import Dict

_last_traded: Dict[str, float] = {}


def mark_traded(coin: str) -> None:
    _last_traded[coin.upper()] = time.monotonic()


def is_on_cooldown(coin: str, cooldown_minutes: float) -> bool:
    ts = _last_traded.get(coin.upper())
    if ts is None:
        return False
    return (time.monotonic() - ts) < cooldown_minutes * 60


def reset() -> None:
    _last_traded.clear()
