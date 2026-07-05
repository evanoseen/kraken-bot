"""Coin blacklist (Day 39).

Reads a comma-separated list of coin tickers from COIN_BLACKLIST and
exposes a fast set-based lookup. Case-insensitive.

Usage:
    from blacklist import is_blacklisted
    if is_blacklisted("DOGE"):
        continue

Set COIN_BLACKLIST=DOGE,SHIB,XRP in .env to skip those coins entirely.
Leave unset (or empty) to allow all coins.
"""
from __future__ import annotations

import os


def get_blacklist() -> frozenset[str]:
    raw = os.getenv("COIN_BLACKLIST", "")
    return frozenset(c.strip().upper() for c in raw.split(",") if c.strip())


def is_blacklisted(coin: str) -> bool:
    return coin.upper() in get_blacklist()
