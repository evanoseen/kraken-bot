"""Day 25 contract: --once and --dry-run CLI flags for main.py.

Three behaviors pinned:
1. --once: exactly one cycle runs, main() returns 0, scheduler never starts.
2. No --once: one cycle runs, then schedule.every() is called (loop entered).
3. --dry-run: os.environ["DRY_RUN"] is "true" before any cycle runs.
4. --once --dry-run together: single cycle, DRY_RUN env set, returns 0 (done-when).

trader.run_trading_cycle and heartbeat.write_heartbeat are always mocked so no
real trading, Kraken calls, or filesystem writes happen in these tests.
"""
from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def restore_dry_run_env():
    """Restore DRY_RUN after each test so flag tests don't bleed into each other."""
    original = os.environ.get("DRY_RUN")
    yield
    if original is None:
        os.environ.pop("DRY_RUN", None)
    else:
        os.environ["DRY_RUN"] = original


@pytest.fixture()
def patched(mocker):
    """Patch the cycle internals and schedule so tests never block or trade."""
    mock_cycle = mocker.patch("trader.run_trading_cycle")
    mock_heartbeat = mocker.patch("heartbeat.write_heartbeat")
    mock_every = mocker.patch("schedule.every")
    mock_every.return_value.minutes.do.return_value = None
    # Break the scheduler while-loop on first sleep so tests that enter it exit cleanly.
    mocker.patch("time.sleep", side_effect=KeyboardInterrupt)
    return mock_cycle, mock_heartbeat, mock_every


# ─── --once ───────────────────────────────────────────────────────────────


def test_once_runs_exactly_one_cycle(patched):
    mock_cycle, _, _ = patched
    import main
    main.main(["--once"])
    assert mock_cycle.call_count == 1


def test_once_returns_zero(patched):
    import main
    assert main.main(["--once"]) == 0


def test_once_skips_scheduler(patched):
    _, _, mock_every = patched
    import main
    main.main(["--once"])
    mock_every.assert_not_called()


# ─── no --once (scheduler mode) ───────────────────────────────────────────


def test_no_once_enters_scheduler_loop(patched):
    _, _, mock_every = patched
    import main
    with pytest.raises(KeyboardInterrupt):
        main.main([])
    mock_every.assert_called_once()


# ─── --dry-run ────────────────────────────────────────────────────────────


def test_dry_run_sets_env_var(patched, monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    import main
    main.main(["--once", "--dry-run"])
    assert os.environ.get("DRY_RUN") == "true"


def test_dry_run_env_not_set_without_flag(patched, monkeypatch):
    monkeypatch.delenv("DRY_RUN", raising=False)
    import main
    main.main(["--once"])
    assert os.environ.get("DRY_RUN") is None


# ─── done-when: --once --dry-run exits 0 ─────────────────────────────────


def test_once_and_dry_run_together_exits_zero(patched):
    import main
    assert main.main(["--once", "--dry-run"]) == 0
