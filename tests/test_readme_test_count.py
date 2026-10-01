"""Day 103: README's "N test files / M tests" claims must match reality.

Day 102 found the two README mentions ("57 test files / 480 tests") stale by
16 tests after four days of test-adding commits, and fixed them by hand.
Its own journal "Next" noted that nothing enforces this the way
tests/test_env_example.py enforces .env.example against config.py — this
test closes that gap the same way: derive both sides from the real
filesystem/collection output, not from a number someone has to remember to
bump.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
TESTS_DIR = REPO_ROOT / "tests"

# Matches both README phrasings: "57 test files / 496 tests" and
# "57 test files (496 tests)".
COUNT_PATTERN = re.compile(r"(\d+)\s+test files\s*[/(]\s*(\d+)\s+tests")


def _readme_counts() -> list[tuple[int, int]]:
    """Every (file_count, test_count) pair README.md claims."""
    matches = COUNT_PATTERN.findall(README.read_text())
    return [(int(files), int(tests)) for files, tests in matches]


def _real_test_file_count() -> int:
    return len(list(TESTS_DIR.glob("*.py")))


def _real_collected_test_count() -> int:
    """Mirrors `pytest --collect-only -q`'s own count, via the same
    interpreter running this test so it uses the active venv."""
    cmd = [sys.executable, "-m", "pytest", "--collect-only", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    match = re.search(r"(\d+) tests collected", result.stdout)
    assert match, f"Could not parse collected test count from:\n{result.stdout}\n{result.stderr}"
    return int(match.group(1))


def test_readme_mentions_the_real_test_file_and_test_counts():
    counts = _readme_counts()
    assert counts, "Expected at least one 'N test files / M tests' mention in README.md"

    real_files = _real_test_file_count()
    real_tests = _real_collected_test_count()

    stale = [c for c in counts if c != (real_files, real_tests)]
    assert not stale, (
        f"README.md claims {stale} but reality is "
        f"({real_files} test files, {real_tests} tests) — "
        f"update the README mentions (mirrors Day 102's fix)."
    )


def test_readme_has_both_known_mentions():
    """Guards against the regex silently matching zero lines (e.g. a future
    README rewording dropping the phrasing), which would pass the test
    above vacuously."""
    assert len(_readme_counts()) >= 2, (
        "Expected at least the Project Structure tree and Tech Stack bullet "
        "mentions of the test count in README.md"
    )
