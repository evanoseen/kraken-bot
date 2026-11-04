"""Day 137: lock the Day 122 requirements.txt / requirements-dev.txt split.

ISA.md's ISC-45 claims requirements.txt holds exactly the runtime deps
main.py (and the scripts it shares local modules with) actually imports,
and that none of the dev/CI tooling in requirements-dev.txt leaks into it.
That claim had zero verification entry in ISA.md and zero test anywhere in
tests/ — this file closes both gaps, modeled on test_env_example.py's
AST-over-hardcoded-list approach so it can't itself go stale the way a
maintained package list would.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# Mirrors tests/test_env_example.py's _SOURCE_FILES scope: every root .py
# module plus scripts/ — everything that runs on the VPS and therefore
# needs its imports satisfied by requirements.txt alone.
_RUNTIME_SOURCE_FILES = sorted(REPO_ROOT.glob("*.py")) + sorted((REPO_ROOT / "scripts").glob("*.py"))

# Import name -> real PyPI distribution name, for the handful of packages
# where they differ. Anything not listed here is assumed to share its
# import name with its package name.
_IMPORT_TO_PACKAGE = {
    "dotenv": "python-dotenv",
}

# Known dev/CI-only tools (requirements-dev.txt) that must never leak into
# the runtime-only requirements.txt, named explicitly so a regression
# fails with a readable package name instead of just a set mismatch.
_DEV_TOOL_MARKERS = {
    "pytest",
    "pytest-mock",
    "pytest-cov",
    "mypy",
    "pip-audit",
    "bandit",
    "types-requests",
}


def _local_module_names() -> set[str]:
    return {p.stem for p in _RUNTIME_SOURCE_FILES}


def _top_level_imports_in(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                names.add(node.module.split(".")[0])
    return names


def _third_party_runtime_packages() -> set[str]:
    """Every third-party package the bot's real runtime code imports,
    across every root module and scripts/ — not just main.py, since scripts
    run standalone on the VPS via their own cron entries (OPS_RUNBOOK.md)
    and need their own imports satisfied by requirements.txt too."""
    local = _local_module_names()
    stdlib = set(sys.stdlib_module_names)
    imports: set[str] = set()
    for path in _RUNTIME_SOURCE_FILES:
        imports |= _top_level_imports_in(path)
    third_party = imports - stdlib - local
    return {_IMPORT_TO_PACKAGE.get(name, name) for name in third_party}


def _parse_requirements(path: Path) -> set[str]:
    """Package names only (no version specifiers), skipping comments/blanks."""
    names = set()
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        names.add(re.split(r"[<>=\[]", line, maxsplit=1)[0].strip())
    return names


def test_requirements_txt_matches_actual_runtime_imports():
    """ISC-45's core claim: requirements.txt is exactly what the bot's real
    source imports — not a superset (dead weight) and not a subset (a
    missing pin that would only fail on a fresh install)."""
    expected = _third_party_runtime_packages()
    actual = _parse_requirements(REPO_ROOT / "requirements.txt")
    assert expected == actual, (
        f"requirements.txt drifted from real imports — "
        f"missing: {sorted(expected - actual)}, extra: {sorted(actual - expected)}"
    )


def test_requirements_dev_txt_does_not_overlap_runtime():
    runtime = _parse_requirements(REPO_ROOT / "requirements.txt")
    dev = _parse_requirements(REPO_ROOT / "requirements-dev.txt")
    assert runtime.isdisjoint(dev), f"packages pinned in both files: {sorted(runtime & dev)}"


def test_known_dev_tools_never_leak_into_runtime_requirements():
    """The Day 122 split's whole point, named explicitly: a test/lint/
    security tool must never end up installed on the production VPS."""
    runtime = _parse_requirements(REPO_ROOT / "requirements.txt")
    leaked = runtime & _DEV_TOOL_MARKERS
    assert not leaked, f"dev-only tooling present in requirements.txt: {sorted(leaked)}"
