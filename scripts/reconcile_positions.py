#!/usr/bin/env python3
"""Day 74: reconcile positions.json against live Kraken holdings.

SECURITY.md's incident-response runbook has always compared positions.json
to the Kraken account ledger — but only as a manual step, during an
incident. This does the same comparison proactively. Meant to run on a
daily cron (see OPS_RUNBOOK.md) so drift — a manual trade, a partial
fill, state corruption — surfaces on its own before it becomes an
incident, instead of being discovered during one.

Usage:
    python3 scripts/reconcile_positions.py
    python3 scripts/reconcile_positions.py --no-alert   # print only, skip Telegram

Exit code is 0 when in sync, 1 when a mismatch is found (an alert is sent
in that case unless --no-alert) — usable as a cron health check on its own.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import notifier  # noqa: E402 — after sys.path insert, so it resolves from repo root
from kraken_client import get_client, get_holdings
from positions import load_positions


def reconcile(kraken_holdings: dict, local_positions: dict) -> tuple[list[str], list[str]]:
    """Return (only_in_kraken, only_in_positions), both sorted coin lists.

    A coin only in Kraken holdings means the exchange has a balance the
    bot isn't tracking (a manual buy, or positions.json lost an entry).
    A coin only in positions.json means the bot thinks it holds something
    Kraken doesn't show (a manual sell, a partial fill, stale state).
    """
    kraken_coins = set(kraken_holdings)
    position_coins = set(local_positions)
    only_in_kraken = sorted(kraken_coins - position_coins)
    only_in_positions = sorted(position_coins - kraken_coins)
    return only_in_kraken, only_in_positions


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Reconcile positions.json against live Kraken holdings.")
    parser.add_argument("--no-alert", action="store_true",
                         help="Print only, skip the Telegram alert on mismatch.")
    args = parser.parse_args(argv)

    client = get_client()
    kraken_holdings = get_holdings(client)
    local_positions = load_positions()

    only_in_kraken, only_in_positions = reconcile(kraken_holdings, local_positions)

    if not only_in_kraken and not only_in_positions:
        print(f"reconcile OK — {len(local_positions)} position(s), Kraken and positions.json agree")
        return 0

    lines = ["POSITIONS MISMATCH"]
    if only_in_kraken:
        lines.append(f"Held on Kraken, not tracked in positions.json: {', '.join(only_in_kraken)}")
    if only_in_positions:
        lines.append(f"Tracked in positions.json, not held on Kraken: {', '.join(only_in_positions)}")
    print("\n".join(lines), file=sys.stderr)

    if not args.no_alert:
        notifier.notify_reconciliation_mismatch(only_in_kraken, only_in_positions)

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
