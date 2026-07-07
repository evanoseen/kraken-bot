"""Per-coin trade counter (Day 41).

Tracks how many times each coin has been traded this session and exposes
a cap check. Prevents the bot from over-trading a single ticker when
signals keep firing for it across cycles.

Usage:
    from coin_trade_counter import at_cap, increment
    if at_cap(coin, cfg.max_trades_per_coin):
        continue
    # ... place trade ...
    increment(coin)

Set MAX_TRADES_PER_COIN in .env to enable. Leave unset to allow unlimited
trades per coin.
"""
from __future__ import annotations

from typing import Dict

_counts: Dict[str, int] = {}


def increment(coin: str) -> None:
    key = coin.upper()
    _counts[key] = _counts.get(key, 0) + 1


def get_count(coin: str) -> int:
    return _counts.get(coin.upper(), 0)


def at_cap(coin: str, max_trades: int | None) -> bool:
    if max_trades is None:
        return False
    return get_count(coin) >= max_trades


def reset() -> None:
    _counts.clear()
