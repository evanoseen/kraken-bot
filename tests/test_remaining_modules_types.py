"""Locks the Day 92 type-hint contract on the 16 modules Day 91's mypy
sweep found clean but unpinned: coin_trade_counter.py, cooldown.py,
cycle_timer.py, headline_cache.py, health.py, heartbeat.py, kill_switch.py,
listing_monitor.py, main.py, news_fetcher.py, portfolio.py, positions.py,
pump_detector.py, retry.py, signals.py, trade_logger.py.

market_matcher.py (Day 90/91) was the fourth time this project discovered a
file mypy-clean with nothing pinning it there. Rather than let it happen a
sixteen-times-over fifth time, this test locks all 16 at once. Writing it
surfaced the same gap Day 68 hit for status.py/blacklist.py: "mypy clean"
and "every function fully annotated" are not the same claim. Six functions
across health.py, listing_monitor.py, portfolio.py, positions.py, and
pump_detector.py were mypy-clean via inferred/Any types but had no explicit
annotation on an argument or return — fixed alongside this test rather than
writing a lock test around a partial state.

Mirrors tests/test_config_notifier_status_blacklist_types.py in shape.
"""
from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGETS = [
    REPO_ROOT / "coin_trade_counter.py",
    REPO_ROOT / "cooldown.py",
    REPO_ROOT / "cycle_timer.py",
    REPO_ROOT / "headline_cache.py",
    REPO_ROOT / "health.py",
    REPO_ROOT / "heartbeat.py",
    REPO_ROOT / "kill_switch.py",
    REPO_ROOT / "listing_monitor.py",
    REPO_ROOT / "main.py",
    REPO_ROOT / "news_fetcher.py",
    REPO_ROOT / "portfolio.py",
    REPO_ROOT / "positions.py",
    REPO_ROOT / "pump_detector.py",
    REPO_ROOT / "retry.py",
    REPO_ROOT / "signals.py",
    REPO_ROOT / "trade_logger.py",
]


def test_mypy_clean_on_remaining_modules():
    """Done-when probe verbatim: one mypy invocation across all 16 files, 0 errors."""
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
    """AST audit across all 16 files: every arg and every return is annotated."""
    missing: list[str] = []
    for target in TARGETS:
        missing.extend(_missing_annotations(target))
    assert not missing, "Missing annotations:\n  " + "\n  ".join(missing)
