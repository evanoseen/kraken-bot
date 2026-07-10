"""Tests for Day 44 — minimum hold time before exit."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False
    yield
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False


def _ts(minutes_ago: float) -> str:
    t = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return t.isoformat()


@pytest.fixture()
def base_exit(mocker, monkeypatch, tmp_path):
    """Patches for check_exit_conditions — single coin in a stop-loss situation."""
    monkeypatch.setenv("DRY_RUN", "false")
    monkeypatch.setenv("STOP_LOSS_PCT", "0.10")
    monkeypatch.setenv("TAKE_PROFIT_PCT", "0.25")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "9999")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    client = mocker.MagicMock()
    mocker.patch("trader.get_price", return_value=0.07)   # entry was 0.10 → -30% → stop-loss
    mocker.patch("trader.place_order", return_value={"result": True})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.csv_log")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    return mocker, client


def test_exit_fires_when_hold_time_met(base_exit, monkeypatch, caplog):
    mocker, client = base_exit
    monkeypatch.setenv("MIN_HOLD_MINUTES", "30")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.10,
        "amount_cad": 10.0,
        "timestamp": _ts(60),   # held 60 min — above 30 min floor
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 100.0})
    assert "stop-loss" in caplog.text.lower()


def test_exit_skipped_when_hold_time_not_met(base_exit, monkeypatch, caplog):
    mocker, client = base_exit
    monkeypatch.setenv("MIN_HOLD_MINUTES", "30")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.10,
        "amount_cad": 10.0,
        "timestamp": _ts(5),    # held only 5 min — below 30 min floor
    })
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 100.0})
    assert "stop-loss" not in caplog.text.lower()
    assert "skipping exit" in caplog.text.lower()


def test_zero_min_hold_always_exits(base_exit, monkeypatch, caplog):
    mocker, client = base_exit
    monkeypatch.setenv("MIN_HOLD_MINUTES", "0")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.10,
        "amount_cad": 10.0,
        "timestamp": _ts(0.1),  # held 6 seconds — no floor applied
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 100.0})
    assert "stop-loss" in caplog.text.lower()


def test_stale_exit_bypasses_min_hold(base_exit, monkeypatch, caplog):
    mocker, client = base_exit
    monkeypatch.setenv("MIN_HOLD_MINUTES", "9999")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "1")
    monkeypatch.setenv("STOP_LOSS_PCT", "0.99")   # stop-loss won't fire
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.get_price", return_value=0.099)  # tiny drop, no stop-loss

    mocker.patch("trader.get_position", return_value={
        "entry_price": 0.10,
        "amount_cad": 10.0,
        "timestamp": _ts(120),  # held 2h — over 1h max_position_age → stale exit fires
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 100.0})
    assert "stale" in caplog.text.lower()


def test_default_min_hold_is_zero(monkeypatch):
    monkeypatch.delenv("MIN_HOLD_MINUTES", raising=False)
    import config, importlib
    importlib.reload(config)
    assert config.Config.from_env().min_hold_minutes == 0.0
