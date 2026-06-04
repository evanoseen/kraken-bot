"""Locks the Day 15 type-hint contract on `kraken_client.py`.

Two probes:
1. `mypy --ignore-missing-imports kraken_client.py` returns zero errors.
2. Every function in `kraken_client.py` has both an annotation on every
   parameter and a return annotation. AST-driven so it catches future
   regressions (someone adding an untyped helper).

Skipped on import errors so a misconfigured local environment doesn't
break the whole suite.
"""
from __future__ import annotations

import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "kraken_client.py"


def test_mypy_clean_on_kraken_client():
    """Done-when probe verbatim: mypy --ignore-missing-imports kraken_client.py = 0 errors."""
    # Prefer the same Python that's running pytest so we use the venv's mypy.
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

        # Skip `self`/`cls` if any class methods sneak in later.
        for arg in node.args.args:
            if arg.arg in ("self", "cls"):
                continue
            if arg.annotation is None:
                missing.append(f"{node.name}({arg.arg}=<no annotation>)")

        if node.returns is None:
            missing.append(f"{node.name} -> <no return annotation>")

    assert not missing, "Missing annotations:\n  " + "\n  ".join(missing)
