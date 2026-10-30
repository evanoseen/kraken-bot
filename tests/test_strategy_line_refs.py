"""Day 132: STRATEGY.md's `file.py:N` line citations must point at real lines.

Days 126/127/129's doc-drift sweeps each found a *prose* claim (a field
list, a coverage percentage) that had gone stale against the code it
described. This is the same failure mode one level more literal: STRATEGY.md
cites six exact `file.py:N` line numbers as pointers into the source
("Confidence math (in `trader.py:130`)", etc.) so a reader can jump straight
to the code. All six had drifted — every one of them now lands on an
unrelated line, a few lines off the real one after later edits shifted the
file without anyone updating the citation. A line number is exactly the kind
of fact Day 123's `scripts/next_day.py` docstring already named as the
risky one ("function/file names survive refactors; numbers drift"), and
nothing was watching these.

This locks each citation to the real line by deriving the (file, line) pairs
from STRATEGY.md's own text — the same `_local_link_targets`-style parse
`test_markdown_links.py` uses for link targets — paired with a hardcoded
substring that line is expected to contain. If a future edit to trader.py,
pump_detector.py, or market_matcher.py shifts one of these lines again
without updating STRATEGY.md, the corresponding substring check fails and
names exactly which citation went stale.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STRATEGY_MD = REPO_ROOT / "STRATEGY.md"

_LINE_CITATION = re.compile(r"`([\w./]+\.py):(\d+)`")

# One expected substring per citation, in the order they appear in
# STRATEGY.md. Each names the real content this project's Day 132 survey
# confirmed sits on that citation's claimed line.
EXPECTED_SUBSTRINGS = [
    "5_000_000",
    "min_volume_multiplier=3.0",
    '0.65 + (p["volume_spike"] / 50)',
    'model="claude-opus-4-6"',
    "def check_exit_conditions",
    "coin not in holdings",
]


def _citations() -> list[tuple[str, int]]:
    text = STRATEGY_MD.read_text()
    return [(file, int(line)) for file, line in _LINE_CITATION.findall(text)]


def test_every_strategy_md_line_citation_matches_its_claimed_content():
    citations = _citations()
    mismatches = []
    for (file, line), expected in zip(citations, EXPECTED_SUBSTRINGS):
        source_lines = (REPO_ROOT / file).read_text().splitlines()
        actual = source_lines[line - 1] if 0 < line <= len(source_lines) else ""
        if expected not in actual:
            mismatches.append(
                f"STRATEGY.md cites `{file}:{line}` expecting it to contain "
                f"{expected!r}, but that line reads: {actual!r}"
            )

    assert not mismatches, (
        "STRATEGY.md's line citation(s) have drifted from the code they "
        "point at:\n" + "\n".join(mismatches)
    )


def test_scan_actually_finds_the_known_line_citations():
    """Guards against the regex silently matching zero citations (e.g. a
    future docs rewrite changing citation syntax), which would pass the
    test above vacuously the same way test_readme_test_count.py's and
    test_markdown_links.py's sibling checks do."""
    citations = _citations()
    assert len(citations) == len(EXPECTED_SUBSTRINGS), (
        f"Expected {len(EXPECTED_SUBSTRINGS)} `file.py:N` line citations in "
        f"STRATEGY.md, found {len(citations)} -- scan may be broken, or a "
        "citation was added/removed without updating EXPECTED_SUBSTRINGS."
    )
