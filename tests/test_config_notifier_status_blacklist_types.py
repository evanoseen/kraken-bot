"""Locks the Day 68 type-hint contract on config.py, notifier.py,
status.py, and blacklist.py.

Day 66 found the hard way what happens without a test like this one:
mypy 1.19.1 stopped honoring mypy.ini's follow_imports=silent, and two
latent type errors in config.py/notifier.py surfaced as *unrelated*
test failures with zero code change of their own — nobody was pinning
these four files' clean state, so nothing caught the regression until
it broke something else. As of Day 68, both were already fixed and
status.py/blacklist.py were already fully typed (the backlog entry's
premise that they had "no type hints at all" was wrong) — this test
exists so that stays true instead of being re-discovered by accident
again.

Mirrors tests/test_kraken_client_types.py and tests/test_trader_types.py
in shape.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    REPO_ROOT / "config.py",
    REPO_ROOT / "notifier.py",
    REPO_ROOT / "status.py",
    REPO_ROOT / "blacklist.py",
]


def test_mypy_clean_on_config_notifier_status_blacklist():
    """Done-when probe verbatim: one mypy invocation across all four files, 0 errors."""
    cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", *[str(t) for t in TARGETS]]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 0, (
        f"mypy reported errors:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def _missing_annotations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is None:
                missing.append(f"{path.name}:{node.name}({arg.arg}=<no annotation>)")
        if node.returns is None:
            missing.append(f"{path.name}:{node.name} -> <no return annotation>")
    return missing


def test_every_function_has_full_type_hints():
    """AST audit across all four files: every arg and every return is annotated."""
    missing: list[str] = []
    for target in TARGETS:
        missing.extend(_missing_annotations(target))
    assert not missing, "Missing annotations:\n  " + "\n  ".join(missing)
