"""Day 139: OPS_RUNBOOK.md never once mentioned `scripts/daily_pnl.py`.

Section 3 ("Log inspection") documents three of the four operational
scripts rsynced to the VPS (README.md's own file-tree comments group
`archive_trades.py`, `check_heartbeat.py`, `daily_pnl.py`, and
`reconcile_positions.py` together, distinct from the two backlog-picker
tools `daily.sh`/`next_day.py`) with their own subsection, concrete `ssh`
commands, and a real CLI flag or two — except `daily_pnl.py`, which had
zero mentions anywhere in the file despite being the one script that
answers "how has the bot actually done?" and fetches the live Kraken
balance, exactly the kind of thing an ops runbook exists to document.

Modeled on tests/test_requirements_split.py's AST-over-hardcoded-list
approach: rather than hardcoding the flag list (which could itself drift
the same way the doc did), it derives the real `--flag` names straight
from `daily_pnl.py`'s own `argparse` calls and asserts each one is
actually documented, not just the bare filename.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS_RUNBOOK = REPO_ROOT / "OPS_RUNBOOK.md"
DAILY_PNL = REPO_ROOT / "scripts" / "daily_pnl.py"


def _argparse_flags(path: Path) -> set[str]:
    """Every `--flag` string passed to an `add_argument(...)` call."""
    tree = ast.parse(path.read_text())
    flags = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_argument"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                    flags.add(arg.value)
    return flags


def test_ops_runbook_mentions_daily_pnl_script():
    text = OPS_RUNBOOK.read_text()
    assert "scripts/daily_pnl.py" in text, (
        "OPS_RUNBOOK.md never mentions scripts/daily_pnl.py, the one "
        "operational script (per README.md's own grouping) with no "
        "documented ssh invocation anywhere in the ops runbook"
    )


def test_ops_runbook_documents_every_daily_pnl_flag():
    flags = _argparse_flags(DAILY_PNL)
    assert flags, "expected at least one --flag in daily_pnl.py's argparse setup"
    text = OPS_RUNBOOK.read_text()
    missing = {flag for flag in flags if flag not in text}
    assert not missing, (
        f"OPS_RUNBOOK.md's daily_pnl.py section is missing real CLI flags: {sorted(missing)} "
        "— a flag added to the script was never documented, or the doc's example commands "
        "drifted from the real argparse contract"
    )
