"""Locks the Day 95 type-hint contract on `scripts/`.

Every prior mypy sweep of this project (Days 15/16/68/90/91/92) only ever
targeted the repo-root `.py` files — `scripts/archive_trades.py`,
`scripts/check_heartbeat.py`, `scripts/daily_pnl.py`, and
`scripts/reconcile_positions.py` had never once been run through mypy.
Running it for the first time found a real, live error (not just an
unlocked-but-clean file like the prior five rounds): `archive_trades.py`'s
`archive_csv`/`archive_jsonl` built `kept`/`archived` lists via bare
`x, y = [], []` unpacking, which mypy can't infer a type for
(`var-annotated`). Fixed by giving each an explicit `list[...]` annotation
before writing this lock test — same "fix before locking, not locking
around the gap" approach Day 92 took with `portfolio.py::compute_value`.
The other three scripts were already mypy-clean and fully annotated.

Mirrors tests/test_remaining_modules_types.py in shape.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    REPO_ROOT / "scripts" / "archive_trades.py",
    REPO_ROOT / "scripts" / "check_heartbeat.py",
    REPO_ROOT / "scripts" / "daily_pnl.py",
    REPO_ROOT / "scripts" / "reconcile_positions.py",
]


def test_mypy_clean_on_scripts():
    """Done-when probe verbatim: one mypy invocation across all 4 files, 0 errors."""
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
    """AST audit across all 4 files: every arg and every return is annotated."""
    missing: list[str] = []
    for target in TARGETS:
        missing.extend(_missing_annotations(target))
    assert not missing, "Missing annotations:\n  " + "\n  ".join(missing)
