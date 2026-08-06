#!/usr/bin/env python3
"""Day 23: daily PnL summary from `trades.jsonl`.

Reads the structured trade log written by `positions.log_trade` (Day 20),
aggregates events by calendar day, and prints a table of buy/sell counts and
net CAD cash flow per day plus a net realized-PnL line. Optionally fetches the
live Kraken balance to answer "what's in the account right now?".

Usage:
    python3 scripts/daily_pnl.py                          # table + live balance
    python3 scripts/daily_pnl.py --no-balance             # skip the Kraken network call
    python3 scripts/daily_pnl.py --file path.jsonl
    python3 scripts/daily_pnl.py --since 2026-07-25 --until 2026-07-31   # one week (Day 60)
    python3 scripts/daily_pnl.py --since 2026-07-25                     # everything from that day on

`--since`/`--until` (Day 60) both take YYYY-MM-DD and are inclusive on both
ends; either can be used alone to leave the other side open.

The aggregation functions are import-safe and network-free so they can be unit
tested; only `fetch_balance()` touches Kraken, and it fails soft.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TRADES_FILE = ROOT / "trades.jsonl"


def load_trades(path: Path) -> list[dict]:
    """Return the list of trade events from a JSONL file, or [] if absent.

    Malformed lines are skipped (logged to stderr) rather than aborting the
    whole summary — a single truncated write shouldn't blind the report.
    """
    if not path.exists():
        return []
    trades: list[dict] = []
    with path.open() as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                trades.append(json.loads(line))
            except json.JSONDecodeError:
                print(f"warning: skipping malformed line {lineno} in {path}", file=sys.stderr)
    return trades


def _day(trade: dict) -> str:
    """Return the calendar-day key (YYYY-MM-DD) from a trade's ISO timestamp."""
    return str(trade.get("timestamp", ""))[:10] or "unknown"


def aggregate_by_day(trades: list[dict]) -> dict[str, dict]:
    """Aggregate trades into per-day buy/sell counts, cash flow, and realized PnL.

    `net_cad` is cash flow: sell proceeds (cash in) minus buy spend (cash out).
    `realized_pnl` sums `pnl_cad`, which is only present on sells.
    Returns an ordered dict keyed by day string, sorted ascending.
    """
    agg: dict[str, dict] = {}
    for t in trades:
        day = _day(t)
        bucket = agg.setdefault(
            day, {"buys": 0, "sells": 0, "net_cad": 0.0, "realized_pnl": 0.0}
        )
        side = str(t.get("side", "")).lower()
        amount = float(t.get("amount_cad") or 0.0)
        pnl = t.get("pnl_cad")
        if side == "buy":
            bucket["buys"] += 1
            bucket["net_cad"] -= amount
        elif side == "sell":
            bucket["sells"] += 1
            bucket["net_cad"] += amount
            if pnl is not None:
                bucket["realized_pnl"] += float(pnl)
    return {day: agg[day] for day in sorted(agg)}


def _parse_date_arg(value: str) -> str:
    """argparse `type=` for --since/--until: validate YYYY-MM-DD, pass through unchanged.

    Kept as a string (not a date object) since `_day()` already produces
    YYYY-MM-DD strings and lexicographic comparison on that format sorts
    correctly — no need to round-trip through date objects.
    """
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {value!r}, expected YYYY-MM-DD")
    return value


def filter_by_range(trades: list[dict], since: Optional[str], until: Optional[str]) -> list[dict]:
    """Keep only trades whose calendar-day key falls within [since, until].

    Both bounds are inclusive; either may be None to leave that side open.
    """
    return [
        t for t in trades
        if (since is None or _day(t) >= since) and (until is None or _day(t) <= until)
    ]


def total_realized_pnl(trades: list[dict]) -> float:
    """Sum `pnl_cad` across all trades that carry it (realized sells)."""
    return sum(float(t["pnl_cad"]) for t in trades if t.get("pnl_cad") is not None)


def format_table(agg: dict[str, dict]) -> str:
    """Render the per-day aggregation as a fixed-width text table."""
    header = f"{'Day':<12} {'Buys':>5} {'Sells':>6} {'Net CAD':>12} {'Realized PnL':>14}"
    sep = "-" * len(header)
    rows = [header, sep]
    if not agg:
        rows.append("(no trades recorded yet)")
        return "\n".join(rows)
    for day, b in agg.items():
        rows.append(
            f"{day:<12} {b['buys']:>5} {b['sells']:>6} "
            f"{b['net_cad']:>+12.2f} {b['realized_pnl']:>+14.2f}"
        )
    return "\n".join(rows)


def fetch_balance() -> Optional[float]:
    """Fetch the live Kraken CAD balance, or None if it can't be reached.

    Imports the trading modules lazily and inside a try/except so a missing
    `.env` or network failure degrades to "balance unavailable" instead of a
    crash — the trade table is still useful offline.
    """
    try:
        sys.path.insert(0, str(ROOT))
        from kraken_client import get_balance, get_client

        return get_balance(get_client())
    except Exception as e:  # noqa: BLE001 — report-only, never fatal
        print(f"warning: could not fetch Kraken balance: {e}", file=sys.stderr)
        return None


def build_report(trades: list[dict], balance: Optional[float]) -> str:
    """Assemble the full text report: table, net PnL line, optional balance."""
    agg = aggregate_by_day(trades)
    lines = [format_table(agg), ""]
    lines.append(f"Net realized PnL: {total_realized_pnl(trades):+.2f} CAD")
    if balance is not None:
        lines.append(f"Current Kraken balance: {balance:.2f} CAD")
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Daily PnL summary from trades.jsonl")
    parser.add_argument("--file", type=Path, default=DEFAULT_TRADES_FILE,
                        help="Path to the trades JSONL file")
    parser.add_argument("--no-balance", action="store_true",
                        help="Skip the live Kraken balance fetch")
    parser.add_argument("--since", type=_parse_date_arg, default=None,
                        help="Only include trades on/after this date (YYYY-MM-DD)")
    parser.add_argument("--until", type=_parse_date_arg, default=None,
                        help="Only include trades on/before this date (YYYY-MM-DD)")
    args = parser.parse_args(argv)

    if args.since and args.until and args.since > args.until:
        parser.error(f"--since {args.since} is after --until {args.until}")

    trades = load_trades(args.file)
    trades = filter_by_range(trades, args.since, args.until)
    balance = None if args.no_balance else fetch_balance()
    print(build_report(trades, balance))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
