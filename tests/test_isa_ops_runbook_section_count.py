"""Day 146: ISA.md's ISC-7 Verification-section row claimed `OPS_RUNBOOK.md`
had "9 numbered sections as of Day 74", a count
written during the Day 79 re-verification pass. Section 10 ("Maintenance
cadence") was added on Day 88 to document the weekly Dependabot review
cadence, but nothing ever came back to bump ISC-7's count or day reference
to match — the same "doc claim nothing derives from source" shape Days
102/103/125/126/127/129/134 each found once already, just living in a
different ISC row.

Derives the real top-level section count from OPS_RUNBOOK.md's own `## N.`
headers instead of hardcoding it, so a future section addition or removal
fails this test immediately rather than waiting for another manual sweep.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"
OPS_RUNBOOK = REPO_ROOT / "OPS_RUNBOOK.md"

ISC_7_LINE_PATTERN = re.compile(
    r"ISC-7: `OPS_RUNBOOK\.md` — (\d+) numbered sections as of Day \d+"
)


def _real_section_count() -> int:
    headers = re.findall(r"^## \d+\. ", OPS_RUNBOOK.read_text(), re.MULTILINE)
    return len(headers)


def test_ops_runbook_has_more_than_six_sections():
    # sanity check that the extraction method is actually finding headers
    assert _real_section_count() >= 6


def test_isa_isc7_section_count_claim_matches_reality():
    match = ISC_7_LINE_PATTERN.search(ISA.read_text())
    assert match, "Expected an ISC-7 '... numbered sections as of Day N' line in ISA.md's Verification section"
    claimed_count = int(match.group(1))
    real_count = _real_section_count()
    assert claimed_count == real_count, (
        f"ISA.md's ISC-7 line claims OPS_RUNBOOK.md has {claimed_count} numbered sections, "
        f"but it actually has {real_count} — a section was added or removed without the claim being updated"
    )
