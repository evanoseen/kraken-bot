"""Day 143: lock DAILY_ITERATIONS.md's own Result notes against JOURNAL.md.

Days 141/142's own closing notes named this as the next "what's missing" /
own-history-as-checklist candidate, applied one level further out than Day
141's ISA.md Decisions-log backfill: JOURNAL.md's job is "one entry per
day," but it also uses dated catch-up blocks (e.g. "## Days 66-83
catch-up") to cover runs of days that shipped with good commit messages
but no individual paragraph, same convention as the real per-day headers.

Walking DAILY_ITERATIONS.md's own Day-N entries that already carry a
`**Result` paragraph (the convention that became consistent from Day 84
onward) against every day JOURNAL.md actually covers -- via its own
headers and catch-up ranges -- found a real six-day gap: Days 84 through
89 each shipped with a full Why/Do/Done-when/Result entry, but never got
a JOURNAL.md paragraph, individually or as part of a catch-up block (the
"Days 66-83 catch-up" block, written the same day Day 84 itself shipped,
stops at 83; the next real entry starts at Day 90). Backfilled as "##
Days 84-89 catch-up" in JOURNAL.md.

Modeled on tests/test_requirements_split.py's and
tests/test_ops_runbook_daily_pnl.py's AST/regex-over-hardcoded-list
approach: both day sets are derived from the real files' own headers, not
a maintained list, so neither this test nor the gap it closes can go
stale the same way silently again -- a future day that ships a `**Result`
paragraph without ever getting a JOURNAL.md mention fails this test by
name.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DAILY_ITERATIONS = REPO_ROOT / "DAILY_ITERATIONS.md"
JOURNAL = REPO_ROOT / "JOURNAL.md"

DAY_HEADER_RE = re.compile(r"^## Day (\d+):", re.MULTILINE)


def _result_backed_days(text: str) -> set[int]:
    """Every Day-N entry in DAILY_ITERATIONS.md that has a `**Result` paragraph."""
    headers = list(DAY_HEADER_RE.finditer(text))
    days = set()
    for i, m in enumerate(headers):
        start = m.end()
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        if "**Result" in text[start:end]:
            days.add(int(m.group(1)))
    return days


def _journal_covered_days(text: str) -> set[int]:
    """Every day JOURNAL.md covers, via a real `## Day N` header or a
    `## Days X-Y [& A-B] catch-up`/`swap` range, the same two header
    shapes this file actually uses."""
    days = set()
    for line in text.splitlines():
        if not line.startswith("## Day"):
            continue
        header = line[3:].split(",")[0]
        for a, b in re.findall(r"(\d+)-(\d+)", header):
            days.update(range(int(a), int(b) + 1))
        stripped = re.sub(r"\d+-\d+", "", header)
        days.update(int(n) for n in re.findall(r"\d+", stripped))
    return days


def test_every_result_backed_day_has_a_journal_entry():
    daily_text = DAILY_ITERATIONS.read_text()
    journal_text = JOURNAL.read_text()

    shipped = _result_backed_days(daily_text)
    covered = _journal_covered_days(journal_text)

    assert shipped, "expected at least one Day-N entry with a **Result paragraph"
    missing = sorted(shipped - covered)
    assert not missing, (
        f"DAILY_ITERATIONS.md days with a **Result paragraph but no JOURNAL.md "
        f"mention (standalone entry or catch-up range): {missing}"
    )
