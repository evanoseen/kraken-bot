"""Tests for Day 31 — stale position force-exit."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
import pytest
import trader


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


@pytest.fixture()
def exit_setup(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "24")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_price", return_value=0.05)
    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    client = mocker.Mock()
    return mocker, client


def test_fresh_position_not_force_sold(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(1),
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "stale" not in caplog.text.lower()


def test_stale_position_logs_warning(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(25),
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "stale position" in caplog.text.lower()


def test_stale_position_dry_run_does_not_call_place_order(exit_setup):
    mocker, client = exit_setup
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(25),
    })
    trader.check_exit_conditions(client, {"DOGE": 200.0})
    trader.place_order.assert_not_called()


def test_stale_skips_stop_loss_check(exit_setup, caplog):
    mocker, client = exit_setup
    # Price down 50% — would trigger stop-loss, but stale check fires first
    mocker.patch("trader.get_price", return_value=0.025)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0, "timestamp": _iso(25),
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "stale position" in caplog.text.lower()
    assert "stop-loss" not in caplog.text.lower()


def test_missing_timestamp_falls_through_to_normal_checks(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.05, "amount_cad": 10.0,
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 200.0})
    assert "stale" not in caplog.text.lower()
