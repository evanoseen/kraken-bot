"""Day 24 contract: a KILL file halts the trading cycle before any network call.

Two layers pinned:
1. `kill_switch.kill_switch_active()` is a pure filesystem probe — True iff the
   file exists, False otherwise.
2. `trader.run_trading_cycle()` short-circuits when the switch is active: it logs
   a warning, places no orders, and never even builds a Kraken client.
"""
from __future__ import annotations

import logging

import pytest

import kill_switch
import trader


# ─── Layer 1: the probe ───────────────────────────────────────────────────


def test_kill_switch_inactive_when_file_absent(tmp_path):
    assert kill_switch.kill_switch_active(tmp_path / "KILL") is False


def test_kill_switch_active_when_file_present(tmp_path):
    target = tmp_path / "KILL"
    target.touch()
    assert kill_switch.kill_switch_active(target) is True


# ─── Layer 2: the cycle short-circuits ────────────────────────────────────


def test_cycle_halts_and_logs_when_kill_active(mocker, caplog):
    """An active kill switch stops the cycle cold — no client, clean warning."""
    mocker.patch.object(trader, "kill_switch_active", return_value=True)
    get_client = mocker.patch.object(trader, "get_client")

    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()

    assert "KILL switch active" in caplog.text
    get_client.assert_not_called()  # halted before any network call


def test_cycle_runs_when_kill_inactive(mocker):
    """With the switch off, the cycle proceeds far enough to build a client."""
    mocker.patch.object(trader, "kill_switch_active", return_value=False)
    get_client = mocker.patch.object(trader, "get_client")
    # Stop the cycle right after the client is built so we don't exercise the
    # whole pipeline — we only need to prove the kill check didn't short-circuit.
    get_client.side_effect = RuntimeError("stop here")

    with pytest.raises(RuntimeError, match="stop here"):
        trader.run_trading_cycle()

    get_client.assert_called_once()
