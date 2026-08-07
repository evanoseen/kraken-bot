#!/usr/bin/env python3
"""Day 61: alert when the heartbeat goes stale.

Day 52 added a Telegram alert on *graceful* shutdown, but a hard crash or a
hung process (OOM, deadlock, a wedged event loop) leaves `last_run.txt`
(Day 21) frozen with no signal at all — this closes that gap.

Run this from an EXTERNAL cron, not on the VPS itself: if the whole VPS is
wedged or down, a cron job running on that same VPS can't alert on it
either. See OPS_RUNBOOK.md's "Heartbeat monitoring" section for the
external cron setup this is meant to run under.

Usage:
    # Local file (mostly useful for testing, or running directly on the VPS)
    python3 scripts/check_heartbeat.py --file /root/kraken-bot/last_run.txt

    # From an external machine: pull the timestamp over SSH first
    python3 scripts/check_heartbeat.py \\
        --timestamp "$(ssh root@204.168.204.221 'cat /root/kraken-bot/last_run.txt')"

    # Custom staleness threshold (default: 2x RUN_INTERVAL_MINUTES from config)
    python3 scripts/check_heartbeat.py --file last_run.txt --threshold-minutes 30

Exit code is 0 when the heartbeat is fresh, 1 when stale or missing (an
alert was sent in that case) — usable as a cron health check on its own.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import notifier  # noqa: E402 — after sys.path insert, so it resolves from repo root


def _parse_timestamp(raw: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp, treating naive values as UTC (matches
    `heartbeat.write_heartbeat`'s `datetime.now(timezone.utc).isoformat()`)."""
    raw = raw.strip()
    if not raw:
        return None
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def read_timestamp_from_file(path: Path) -> Optional[datetime]:
    try:
        return _parse_timestamp(path.read_text())
    except FileNotFoundError:
        return None


def staleness_minutes(heartbeat: datetime, now: Optional[datetime] = None) -> float:
    now = now or datetime.now(timezone.utc)
    return (now - heartbeat).total_seconds() / 60.0


def check(
    heartbeat: Optional[datetime], threshold_minutes: float, now: Optional[datetime] = None
) -> tuple[bool, Optional[float]]:
    """Return (is_stale, age_minutes). A missing heartbeat counts as stale;
    age_minutes is None in that case since there's nothing to measure."""
    if heartbeat is None:
        return True, None
    age = staleness_minutes(heartbeat, now)
    return age > threshold_minutes, age


def _default_threshold_minutes() -> float:
    """2x RUN_INTERVAL_MINUTES from config, or a 30 minute fallback if
    config/.env isn't available — this script is meant to also run from a
    machine that doesn't have the bot's own environment set up."""
    try:
        from config import cfg
        return 2 * cfg.run_interval_minutes
    except Exception:
        return 30.0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Alert via Telegram if the bot's heartbeat has gone stale.")
    parser.add_argument("--file", type=Path, default=None, help="Path to a local last_run.txt")
    parser.add_argument("--timestamp", type=str, default=None,
                         help="Heartbeat ISO timestamp directly, e.g. fetched over SSH")
    parser.add_argument("--threshold-minutes", type=float, default=None,
                         help="Staleness threshold in minutes (default: 2x RUN_INTERVAL_MINUTES)")
    args = parser.parse_args(argv)

    if args.timestamp is not None:
        heartbeat = _parse_timestamp(args.timestamp)
    else:
        heartbeat = read_timestamp_from_file(args.file or (ROOT / "last_run.txt"))

    threshold = args.threshold_minutes if args.threshold_minutes is not None else _default_threshold_minutes()
    is_stale, age = check(heartbeat, threshold)

    if not is_stale:
        print(f"heartbeat OK — {age:.1f}m old (threshold {threshold:.0f}m)")
        return 0

    if age is None:
        print("heartbeat MISSING — last_run.txt not found or unreadable.", file=sys.stderr)
    else:
        print(f"heartbeat STALE — {age:.1f}m old (threshold {threshold:.0f}m).", file=sys.stderr)
    notifier.notify_heartbeat_stale(age, threshold)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
