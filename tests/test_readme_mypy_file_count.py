"""Day 125: README's "mypy ... across all N source files" claim, and the
set of files tests/test_*_types.py actually locks, must both match the
real repo-root + scripts/ file set.

Day 123 added scripts/next_day.py but nothing added it to a TARGET/TARGETS
list that day — mypy-clean with nothing pinning it there, the same "mypy
clean but unpinned" gap Days 68/90/91/92 each found and closed for a
different file (status.py/blacklist.py, market_matcher.py, and 16 more).
Fixed directly in tests/test_scripts_types.py (Day 125), but that's the
sixth time this exact gap has appeared — this test locks the whole set so
a seventh slips through CI instead of waiting for a future manual sweep,
the same way tests/test_readme_test_count.py (Day 103) stopped README's
test-count bullets from needing a human to remember to bump them. It also
caught README's "27 source files" bullet sitting one behind reality (28)
since Day 123 landed — fixed alongside this test, not by it.
"""
from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
TESTS_DIR = Path(__file__).resolve().parent

SOURCE_FILE_COUNT_PATTERN = re.compile(r"all (\d+) source files")


def _real_source_files() -> set[Path]:
    """Every file the "mypy --ignore-missing-imports *.py scripts/*.py"
    sweep in `make lint`'s own comment covers."""
    root_files = set(REPO_ROOT.glob("*.py"))
    script_files = set((REPO_ROOT / "scripts").glob("*.py"))
    return root_files | script_files


def _locked_files() -> set[Path]:
    """Every file named in a TARGET/TARGETS of a tests/test_*_types.py module."""
    locked: set[Path] = set()
    for test_file in sorted(TESTS_DIR.glob("test_*_types.py")):
        spec = importlib.util.spec_from_file_location(test_file.stem, test_file)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        targets = getattr(module, "TARGETS", None)
        if targets is not None:
            locked.update(targets)
        target = getattr(module, "TARGET", None)
        if target is not None:
            locked.add(target)
    return locked


def test_every_real_source_file_is_locked_by_a_types_test():
    real = _real_source_files()
    locked = _locked_files()
    unlocked = real - locked
    assert not unlocked, (
        f"These source files have no tests/test_*_types.py TARGET/TARGETS "
        f"entry pinning their mypy-clean + full-annotation state: "
        f"{sorted(str(p.relative_to(REPO_ROOT)) for p in unlocked)} "
        f"(mirrors the gap Days 68/90/91/92 each closed for a different file)."
    )
    stale = locked - real
    assert not stale, (
        f"These TARGET/TARGETS entries point at files that no longer exist: "
        f"{sorted(str(p) for p in stale)}"
    )


def test_readme_source_file_count_matches_reality():
    match = SOURCE_FILE_COUNT_PATTERN.search(README.read_text())
    assert match, "Expected an 'all N source files' mention in README.md"
    claimed = int(match.group(1))
    real = len(_real_source_files())
    assert claimed == real, (
        f"README claims {claimed} source files but reality is {real} "
        f"(mirrors Day 102's test-count drift fix)."
    )
