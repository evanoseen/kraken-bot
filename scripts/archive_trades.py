#!/usr/bin/env python3
"""Day 59: archive old trade log entries.

`trades.csv` and `trades.jsonl` (Day 20) are append-only forever, same
problem `bot.log` had before Day 54 rotated it — just slower growing since
a trade is rarer than a log line. This splits entries older than N days
into a dated archive pair, keeping the live files small.

Usage:
    python3 scripts/archive_trades.py                # archive entries older than 90 days
    python3 scripts/archive_trades.py --days 30       # custom cutoff
    python3 scripts/archive_trades.py --dry-run       # report counts, write nothing
    python3 scripts/archive_trades.py --csv path.csv --jsonl path.jsonl

Archived rows are appended to trades_archive_<cutoff-date>.csv/.jsonl next
to the source files, so repeated runs accumulate into the same archive
pair for a given day rather than overwriting older archives on a
different day. The live files are rewritten atomically (write to a temp
file, then os.replace, done implicitly by Path.replace) so a crash
mid-write can't corrupt them.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = ROOT / "trades.csv"
DEFAULT_JSONL = ROOT / "trades.jsonl"
DEFAULT_DAYS = 90


def _parse_timestamp(raw: str) -> Optional[datetime]:
    """Parse an ISO 8601 timestamp, treating naive values as UTC (matches
    `datetime.utcnow().isoformat()` used by `positions.log_trade`)."""
    try:
        ts = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


def archive_csv(path: Path, cutoff: datetime, archive_path: Path, dry_run: bool) -> tuple[int, int]:
    """Split rows older than `cutoff` out of a trades.csv into `archive_path`.

    Returns (archived_count, kept_count). Malformed rows (bad/missing
    timestamp) are always kept in the live file rather than silently
    dropped or mis-archived.
    """
    if not path.exists():
        return 0, 0
    with path.open(newline="") as f:
        rows = list(csv.reader(f))
    if not rows:
        return 0, 0
    header, body = rows[0], rows[1:]

    kept, archived = [], []
    for row in body:
        ts = _parse_timestamp(row[0]) if row else None
        (archived if ts is not None and ts < cutoff else kept).append(row)

    if not archived:
        return 0, len(kept)

    if not dry_run:
        write_header = not archive_path.exists()
        with archive_path.open("a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(header)
            writer.writerows(archived)

        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(kept)
        tmp.replace(path)

    return len(archived), len(kept)


def archive_jsonl(path: Path, cutoff: datetime, archive_path: Path, dry_run: bool) -> tuple[int, int]:
    """Split JSONL lines older than `cutoff` out of a trades.jsonl into
    `archive_path`. Malformed lines are always kept in the live file."""
    if not path.exists():
        return 0, 0

    kept_lines, archived_lines = [], []
    with path.open() as f:
        for raw_line in f:
            line = raw_line.rstrip("\n")
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                ts = _parse_timestamp(event.get("timestamp", ""))
            except json.JSONDecodeError:
                ts = None
            (archived_lines if ts is not None and ts < cutoff else kept_lines).append(line + "\n")

    if not archived_lines:
        return 0, len(kept_lines)

    if not dry_run:
        with archive_path.open("a") as f:
            f.writelines(archived_lines)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text("".join(kept_lines))
        tmp.replace(path)

    return len(archived_lines), len(kept_lines)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Archive trade log entries older than N days.")
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                         help=f"Archive entries older than this many days (default {DEFAULT_DAYS}).")
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="Path to trades.csv")
    parser.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL, help="Path to trades.jsonl")
    parser.add_argument("--dry-run", action="store_true", help="Report counts only, write nothing.")
    args = parser.parse_args(argv)

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    cutoff_label = cutoff.strftime("%Y%m%d")

    csv_archive = args.csv.parent / f"trades_archive_{cutoff_label}.csv"
    jsonl_archive = args.jsonl.parent / f"trades_archive_{cutoff_label}.jsonl"

    csv_archived, csv_kept = archive_csv(args.csv, cutoff, csv_archive, args.dry_run)
    jsonl_archived, jsonl_kept = archive_jsonl(args.jsonl, cutoff, jsonl_archive, args.dry_run)

    prefix = "[DRY RUN] " if args.dry_run else ""
    print(f"{prefix}trades.csv:   {csv_archived} archived, {csv_kept} kept")
    print(f"{prefix}trades.jsonl: {jsonl_archived} archived, {jsonl_kept} kept")
    if not args.dry_run and (csv_archived or jsonl_archived):
        print(f"Archive files: {csv_archive.name}, {jsonl_archive.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
