"""Day 159: lock SECURITY.md section 5's "compromised PyPI package" threat
list against the real requirements.txt.

That sentence was written on Day 8 (`krakenex, anthropic, feedparser,
schedule, python-dotenv, requests`), ten days before Day 18 added
`tenacity` as a runtime dependency — nothing ever went back to add it to
this specific sentence, even though ISA.md's ISC-45 (Day 137,
`tests/test_requirements_split.py`) has separately locked requirements.txt
itself against real imports since. Deriving the expected package set from
requirements.txt directly (not a second hardcoded list) so this can't
itself go stale the same way the original list did.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_THREAT_LINE_PATTERN = re.compile(
    r"A compromised PyPI package \(([^)]+)\) executes arbitrary code"
)


def _runtime_package_names() -> set[str]:
    names = set()
    for line in (REPO_ROOT / "requirements.txt").read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names.add(re.split(r"[<>=\[]", line, maxsplit=1)[0].strip())
    return names


def _security_md_threat_list() -> set[str]:
    text = (REPO_ROOT / "SECURITY.md").read_text()
    match = _THREAT_LINE_PATTERN.search(text)
    assert match, (
        "Expected to find SECURITY.md's \"A compromised PyPI package "
        "(...) executes arbitrary code\" threat-list sentence in section 5"
    )
    return {name.strip() for name in match.group(1).split(",")}


def test_security_md_threat_list_names_every_runtime_dependency():
    """Every real runtime dependency must be named in SECURITY.md's own
    "compromised PyPI package" threat sentence, so a future dependency
    addition can't silently go unnamed the way `tenacity` did for ~150
    days after Day 18 added it."""
    expected = _runtime_package_names()
    actual = _security_md_threat_list()
    assert expected == actual, (
        f"SECURITY.md's compromised-PyPI-package threat list drifted from "
        f"requirements.txt — missing: {sorted(expected - actual)}, "
        f"extra (no longer a real dependency): {sorted(actual - expected)}"
    )
