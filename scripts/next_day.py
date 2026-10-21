#!/usr/bin/env python3
"""Day 123: find the next DAILY_ITERATIONS.md task to run.

`scripts/daily.sh` used to compute "today's task" from a calendar-date
offset since the project's 2026-05-19 start date, on the assumption that
one backlog Day would get done per calendar day. That assumption broke
early (plenty of calendar days had no session at all) and the script was
never actually run to notice: by Day 123 the offset had drifted to "Day
156", 33 days ahead of the real backlog. Every session instead read
DAILY_ITERATIONS.md by hand and used the project's real convention --
the lowest-numbered "## Day N" entry with no "**Result (...)**" paragraph
under it yet. This module makes that the script's actual behavior.

Usage:
    python3 scripts/next_day.py DAILY_ITERATIONS.md
"""
from __future__ import annotations

import re
import sys

_DAY_HEADER = re.compile(r"^## Day (\d+)\b", re.MULTILINE)
_RESULT_MARKER = "**Result ("


def find_next_day(text: str) -> int:
    """Return the next Day number to work on.

    Finds the "## Day N" header with the *highest* N and returns N if it
    has no "**Result (...)**" paragraph yet (still in progress / not done),
    or N + 1 if it does (move on to the next day).

    This deliberately does NOT search for the lowest-numbered Day anywhere
    in the file that lacks a Result: per the file's own "Status note (added
    Day 55...)" section, Days 1-31's originals were picked ad hoc and never
    got Result paragraphs retroactively, Days 29-31 were reused for
    unrelated work and renumbered, and the Result-paragraph convention
    itself only started being applied consistently from Day 84 onward
    (Days 56-83 are done but were never backfilled with one). A whole-file
    scan would resolve to one of those decades-old gaps instead of the
    actual next day, which every session has always picked by reading the
    end of the file, not the start.

    Raises ValueError if `text` has no "## Day N" headers at all.
    """
    headers = list(_DAY_HEADER.finditer(text))
    if not headers:
        raise ValueError("no '## Day N' headers found")

    days = []
    for i, match in enumerate(headers):
        day = int(match.group(1))
        block_start = match.end()
        block_end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        has_result = _RESULT_MARKER in text[block_start:block_end]
        days.append((day, has_result))

    last_day, last_has_result = max(days, key=lambda pair: pair[0])
    return last_day + 1 if last_has_result else last_day


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        print("usage: next_day.py DAILY_ITERATIONS.md", file=sys.stderr)
        return 2

    try:
        with open(argv[0], encoding="utf-8") as f:
            text = f.read()
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    try:
        print(find_next_day(text))
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
