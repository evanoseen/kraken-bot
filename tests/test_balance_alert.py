"""Tests for Day 38 — low balance Telegram alert."""
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
def patched(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.setenv("BALANCE_ALERT_THRESHOLD", "20.0")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    notify = mocker.patch("trader.notify_trade")
    return mocker, notify


def test_no_alert_above_threshold(patched):
    mocker, notify = patched
    mocker.patch("trader.get_balance", return_value=50.0)
    trader.run_trading_cycle()
    calls = [c for c in notify.call_args_list if c.args[0] == "balance_alert"]
    assert len(calls) == 0


def test_alert_fires_below_threshold(patched, caplog):
    mocker, notify = patched
    mocker.patch("trader.get_balance", return_value=15.0)
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "low balance" in caplog.text.lower()
    calls = [c for c in notify.call_args_list if c.args[0] == "balance_alert"]
    assert len(calls) == 1


def test_alert_fires_only_once(patched):
    mocker, notify = patched
    mocker.patch("trader.get_balance", return_value=15.0)
    trader.run_trading_cycle()
    trader.run_trading_cycle()
    calls = [c for c in notify.call_args_list if c.args[0] == "balance_alert"]
    assert len(calls) == 1


def test_no_alert_when_threshold_unset(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())
    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=1.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    notify = mocker.patch("trader.notify_trade")

    trader.run_trading_cycle()
    calls = [c for c in notify.call_args_list if c.args[0] == "balance_alert"]
    assert len(calls) == 0
