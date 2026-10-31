"""Locks STRATEGY.md's claim about MIN_HOLD_MINUTES (Day 133).

Day 44 added a minimum-hold-time guard to `trader.check_exit_conditions`,
but STRATEGY.md's "Exit logic" section never documented it until Day 133 —
the guard existed in code, in `.env.example`, and in its own dedicated
test file (`tests/test_min_hold_minutes.py`) for 89 days with no mention in
the one doc whose job is to describe the exit flow end to end.

Day 133's fix added a table row and subsection claiming the guard runs
right after the stale-position (max-age) check and before trailing
stop/stop-loss/take-profit. This test locks both halves of that claim
against the real source: the doc says the words, and the real check order
in `trader.py` still matches what the doc describes.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRADER = REPO_ROOT / "trader.py"
STRATEGY = REPO_ROOT / "STRATEGY.md"


def _first_line_containing(source: str, needle: str) -> int:
    for i, line in enumerate(source.splitlines(), start=1):
        if needle in line:
            return i
    raise AssertionError(f"{needle!r} not found in trader.py")


def test_strategy_md_documents_min_hold_minutes():
    text = STRATEGY.read_text()
    assert "MIN_HOLD_MINUTES" in text
    assert "Minimum hold time" in text


def test_min_hold_guard_runs_between_stale_exit_and_trailing_stop():
    source = TRADER.read_text()
    stale_line = _first_line_containing(source, "cfg.max_position_age_hours")
    min_hold_line = _first_line_containing(source, "cfg.min_hold_minutes > 0")
    trailing_line = _first_line_containing(source, "cfg.trailing_stop_pct is not None")
    stop_loss_line = _first_line_containing(source, "pct_change <= -cfg.stop_loss_pct")

    assert stale_line < min_hold_line < trailing_line < stop_loss_line, (
        "trader.check_exit_conditions's check order no longer matches "
        "STRATEGY.md's documented order (stale/max-age -> min-hold-time -> "
        "trailing-stop -> stop-loss/take-profit) -- update whichever one "
        "is now wrong"
    )
