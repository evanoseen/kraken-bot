"""Tests for Day 69 — trailing stop-loss exit."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import pytest
import trader


def _iso(hours_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


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


@pytest.fixture()
def exit_setup(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("STOP_LOSS_PCT", "0.10")
    monkeypatch.setenv("TAKE_PROFIT_PCT", "0.25")
    monkeypatch.setenv("MAX_POSITION_AGE_HOURS", "999")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.update_peak_price")
    client = mocker.Mock()
    return mocker, client


def _enable_trailing_stop(monkeypatch, mocker, pct: str):
    monkeypatch.setenv("TRAILING_STOP_PCT", pct)
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())


def test_disabled_by_default(exit_setup, caplog):
    """TRAILING_STOP_PCT unset -> current behavior, unaffected."""
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=110.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 120.0,
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 1.0})
    assert "trailing stop" not in caplog.text.lower()


def test_runs_up_then_drops_triggers_trailing_stop(exit_setup, monkeypatch, caplog):
    """The literal Day 69 done-when: runs up 20%, drops 8% off that peak,
    exits via trailing stop — even though it's still net positive vs. entry
    and would never have hit the fixed 10% stop-loss."""
    mocker, client = exit_setup
    _enable_trailing_stop(monkeypatch, mocker, "0.08")
    # Peak was 120 (entry * 1.20). ~8.3% down from peak = 110 (still +10% vs entry).
    mocker.patch("trader.get_price", return_value=110.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 120.0,
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 1.0})
    assert "trailing stop" in caplog.text.lower()
    assert "stop-loss" not in caplog.text.lower()
    trader.place_order.assert_not_called()  # DRY_RUN=true


def test_never_ran_up_does_not_exit_early(exit_setup, monkeypatch, caplog):
    """Equivalent-magnitude drop, but straight down from entry with no peak
    above entry — trailing stop must not fire, and (at 8% vs. a 10% fixed
    stop-loss) nothing else fires either. No exit at all this cycle."""
    mocker, client = exit_setup
    _enable_trailing_stop(monkeypatch, mocker, "0.08")
    mocker.patch("trader.get_price", return_value=92.0)  # -8% off entry, never went above 100
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
    })
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_exit_conditions(client, {"DOGE": 1.0})
    assert "trailing stop" not in caplog.text.lower()
    assert "stop-loss" not in caplog.text.lower()
    trader.place_order.assert_not_called()


def test_peak_defaults_to_entry_when_no_peak_price_key(exit_setup, monkeypatch, caplog):
    """A position opened before TRAILING_STOP_PCT was ever enabled has no
    peak_price key — must not crash, and must behave like peak == entry."""
    mocker, client = exit_setup
    _enable_trailing_stop(monkeypatch, mocker, "0.05")
    mocker.patch("trader.get_price", return_value=99.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
    })
    trader.check_exit_conditions(client, {"DOGE": 1.0})
    assert "trailing stop" not in caplog.text.lower()


def test_updates_peak_price_when_price_exceeds_it(exit_setup, monkeypatch):
    mocker, client = exit_setup
    _enable_trailing_stop(monkeypatch, mocker, "0.08")
    mocker.patch("trader.get_price", return_value=125.0)  # new high, above stored peak of 120
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 120.0,
    })
    trader.check_exit_conditions(client, {"DOGE": 1.0})
    trader.update_peak_price.assert_called_once_with("DOGE", 125.0)


def test_does_not_rewrite_peak_when_price_has_not_moved(exit_setup, monkeypatch):
    mocker, client = exit_setup
    _enable_trailing_stop(monkeypatch, mocker, "0.50")  # wide enough it never triggers here
    mocker.patch("trader.get_price", return_value=115.0)  # below stored peak of 120
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 120.0,
    })
    trader.check_exit_conditions(client, {"DOGE": 1.0})
    trader.update_peak_price.assert_not_called()


def test_trailing_stop_live_places_order_and_records_pnl(exit_setup, monkeypatch):
    mocker, client = exit_setup
    monkeypatch.setenv("DRY_RUN", "false")
    _enable_trailing_stop(monkeypatch, mocker, "0.08")
    mocker.patch("trader.get_price", return_value=110.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0, "timestamp": _iso(1),
        "peak_price": 120.0,
    })
    trader.check_exit_conditions(client, {"DOGE": 1.0})
    trader.place_order.assert_called_once()
    trader.log_trade.assert_called_once()
    args = trader.log_trade.call_args.args
    assert args[0] == "DOGE"
    assert args[1] == "sell_trailingstop"
    trader.remove_position.assert_called_once_with("DOGE")
    assert trader._wins == 1  # 110 > 100 entry -> net positive
