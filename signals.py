"""Signal deduplication (Day 33).

When the same coin appears in both pump signals and news signals in one cycle,
merging them avoids placing two separate orders on the same asset. The merged
signal takes the higher confidence and concatenates both reasoning strings.

Usage:
    from signals import deduplicate
    merged = deduplicate(pump_signals + news_signals)
"""
from __future__ import annotations

from typing import Any


def deduplicate(signals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[tuple[str, str], dict[str, Any]] = {}
    for sig in signals:
        key = (sig["coin"].upper(), sig["action"].lower())
        if key not in seen:
            seen[key] = dict(sig)
            seen[key]["coin"] = key[0]
        else:
            existing = seen[key]
            if sig["confidence"] > existing["confidence"]:
                existing["confidence"] = sig["confidence"]
            existing["reasoning"] = existing["reasoning"] + " | " + sig["reasoning"]
    return list(seen.values())
