"""Tests for Day 93 — signal-driven exit on a stale buy thesis.

`check_signal_reversal_exits` is a distinct exit path from the
price-threshold checks in `check_exit_conditions` (stop-loss, take-profit,
trailing-stop, max-age): it exits a held coin the moment this cycle's
merged pump+news signal batch carries a fresh "sell" for it, regardless of
current P&L.
"""
from __future__ import annotations

import logging

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


@pytest.fixture()
def exit_setup(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.place_order", return_value={"txid": "x"})
    mocker.patch("trader.log_trade")
    mocker.patch("trader.remove_position")
    mocker.patch("trader.notify_trade")
    mocker.patch("trader.mark_traded")
    mocker.patch("trader.csv_log")
    client = mocker.Mock()
    return mocker, client


def test_reversed_signal_triggers_exit_distinct_from_price_paths(exit_setup, caplog):
    """The literal Day 93 done-when: a fresh sell signal on a held coin
    exits it, even though price never moved enough to hit stop-loss,
    take-profit, or trailing-stop, and the position is nowhere near max age.
    """
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=101.0)  # +1%, no price threshold fires
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0,
    })
    signals = [
        {"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "protocol exploit disclosed"},
    ]
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)
    assert "signal reversal" in caplog.text.lower()
    assert "protocol exploit disclosed" in caplog.text
    assert "stop-loss" not in caplog.text.lower()
    assert "trailing stop" not in caplog.text.lower()
    trader.place_order.assert_not_called()  # DRY_RUN=true


def test_no_reversal_signal_does_not_exit(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=101.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0,
    })
    signals = [
        {"coin": "SHIB", "action": "sell", "confidence": 0.9, "reasoning": "unrelated coin"},
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "still bullish"},
    ]
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)
    assert "signal reversal" not in caplog.text.lower()
    trader.place_order.assert_not_called()


def test_coin_with_no_tracked_position_is_skipped(exit_setup):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=101.0)
    mocker.patch("trader.get_position", return_value=None)
    signals = [{"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "n/a"}]
    trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)
    trader.place_order.assert_not_called()


def test_missing_price_is_skipped(exit_setup):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=None)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0,
    })
    signals = [{"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "n/a"}]
    trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)
    trader.place_order.assert_not_called()


def test_live_places_order_and_records_pnl_regardless_of_direction(exit_setup, monkeypatch):
    """Exits on the reversal even though the position is net negative —
    the trigger is the thesis, not the P&L sign."""
    mocker, client = exit_setup
    monkeypatch.setenv("DRY_RUN", "false")
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.place_order", return_value={"txid": "x"})

    mocker.patch("trader.get_price", return_value=97.0)  # -3%, entry price 100
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0,
    })
    signals = [{"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "reversal"}]
    trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)

    trader.place_order.assert_called_once()
    trader.log_trade.assert_called_once()
    args = trader.log_trade.call_args.args
    assert args[0] == "DOGE"
    assert args[1] == "sell_signalreversal"
    trader.remove_position.assert_called_once_with("DOGE")
    assert trader._losses == 1
    assert trader._wins == 0


def test_action_case_and_coin_case_insensitive(exit_setup, caplog):
    mocker, client = exit_setup
    mocker.patch("trader.get_price", return_value=101.0)
    mocker.patch("trader.get_position", return_value={
        "entry_price": 100.0, "amount_cad": 100.0,
    })
    signals = [{"coin": "doge", "action": "SELL", "confidence": 0.9, "reasoning": "n/a"}]
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.check_signal_reversal_exits(client, {"DOGE": 1.0}, signals)
    assert "signal reversal" in caplog.text.lower()
    trader.place_order.assert_not_called()  # DRY_RUN=true
