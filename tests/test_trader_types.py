"""Locks the Day 16 type-hint contract on `trader.py`.

Two probes:
1. `mypy --ignore-missing-imports trader.py` returns zero errors.
2. Every function in `trader.py` has both an annotation on every
   parameter and a return annotation.

Mirrors `tests/test_kraken_client_types.py` in shape so future
"type module X" days can copy-paste the pattern.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "trader.py"


def test_mypy_clean_on_trader():
    """Done-when probe verbatim: mypy --ignore-missing-imports trader.py = 0 errors."""
    cmd = [sys.executable, "-m", "mypy", "--ignore-missing-imports", str(TARGET)]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO_ROOT)
    assert result.returncode == 0, (
        f"mypy reported errors:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


def test_every_function_has_full_type_hints():
    """AST audit: every function arg has an annotation and every function declares a return type."""
    tree = ast.parse(TARGET.read_text())

    missing: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue

        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is None:
                missing.append(f"{node.name}({arg.arg}=<no annotation>)")

        if node.returns is None:
            missing.append(f"{node.name} -> <no return annotation>")

    assert not missing, "Missing annotations:\n  " + "\n  ".join(missing)
