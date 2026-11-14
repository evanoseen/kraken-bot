"""Day 147: ISA.md's ISC-29 Verification-section row claimed `SECURITY.md`
had "6 numbered sections plus a hardening backlog, re-audited Days 58 and
75", a count last touched during the Day 75 re-audit. Section 7
("Untrusted content reaching the Claude signal pipeline") was added on Day
138 to document the LLM-prompt-injection threat model, but nothing ever
came back to bump ISC-29's count to match — the same "doc claim nothing
derives from source" shape Days 102/103/125/126/127/129/134/146 each found
once already, just living in a different ISC row.

Derives the real top-level section count from SECURITY.md's own `## N.`
headers instead of hardcoding it, so a future section addition or removal
fails this test immediately rather than waiting for another manual sweep.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"
SECURITY = REPO_ROOT / "SECURITY.md"

ISC_29_LINE_PATTERN = re.compile(
    r"ISC-29: `SECURITY\.md`, (\d+) numbered sections as of Day \d+"
)


def _real_section_count() -> int:
    headers = re.findall(r"^## \d+\. ", SECURITY.read_text(), re.MULTILINE)
    return len(headers)


def test_security_md_has_more_than_six_sections():
    # sanity check that the extraction method is actually finding headers
    assert _real_section_count() >= 6


def test_isa_isc29_section_count_claim_matches_reality():
    match = ISC_29_LINE_PATTERN.search(ISA.read_text())
    assert match, "Expected an ISC-29 '... numbered sections as of Day N' line in ISA.md's Verification section"
    claimed_count = int(match.group(1))
    real_count = _real_section_count()
    assert claimed_count == real_count, (
        f"ISA.md's ISC-29 line claims SECURITY.md has {claimed_count} numbered sections, "
        f"but it actually has {real_count} — a section was added or removed without the claim being updated"
    )
