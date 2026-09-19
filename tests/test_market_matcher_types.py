"""Locks the mypy-clean state `market_matcher.py` reached on Day 90.

Day 90's bump of `anthropic` to 1.x fixed a real mypy error in this file
(`message.content[0].text` — the 1.x `ContentBlock` union grew ~10 member
types, most without `.text`) by adding an `isinstance(block,
anthropic.types.TextBlock)` guard. That fix landed clean, but unlike every
other file a daily-iteration day has made mypy-clean (kraken_client.py
Day 15, trader.py Day 16, config.py/notifier.py/status.py/blacklist.py
Day 68), nobody added the matching lock test the same day — found during
the Day 91 backlog-extension sweep. Mirrors tests/test_kraken_client_types.py
and tests/test_config_notifier_status_blacklist_types.py in shape.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET = REPO_ROOT / "market_matcher.py"


def test_mypy_clean_on_market_matcher():
    """mypy --ignore-missing-imports market_matcher.py = 0 errors."""
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
