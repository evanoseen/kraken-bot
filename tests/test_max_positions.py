"""Tests for Day 28 — max open positions limit."""
from __future__ import annotations

import logging
import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    yield
    trader._starting_balance = None
    trader._peak_balance = None


@pytest.fixture()
def patched(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("MAX_OPEN_POSITIONS", "2")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE", "SHIB", "PEPE"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.get_price", return_value=0.05)
    mocker.patch("trader.notify_trade")
    return mocker


def test_buy_allowed_under_limit(patched, caplog):
    patched.patch("trader.get_holdings", return_value={"DOGE": 100.0})
    signals = [{"coin": "SHIB", "action": "buy", "confidence": 0.9, "reasoning": "test"}]
    patched.patch("trader.analyze_news_for_trades", return_value=signals)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "max open positions" not in caplog.text.lower()
    assert "BUY" in caplog.text


def test_buy_blocked_at_limit(patched, caplog):
    patched.patch("trader.get_holdings", return_value={"DOGE": 100.0, "SHIB": 50.0})
    signals = [{"coin": "PEPE", "action": "buy", "confidence": 0.9, "reasoning": "test"}]
    patched.patch("trader.analyze_news_for_trades", return_value=signals)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "max open positions" in caplog.text.lower()


def test_sell_not_blocked_at_limit(patched, caplog):
    patched.patch("trader.get_holdings", return_value={"DOGE": 100.0, "SHIB": 50.0})
    signals = [{"coin": "DOGE", "action": "sell", "confidence": 0.9, "reasoning": "test"}]
    patched.patch("trader.analyze_news_for_trades", return_value=signals)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "max open positions" not in caplog.text.lower()
    assert "SELL" in caplog.text


def test_all_buys_blocked_when_at_limit(patched, caplog):
    patched.patch("trader.get_holdings", return_value={"DOGE": 100.0, "SHIB": 50.0})
    signals = [
        {"coin": "PEPE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
        {"coin": "XRP", "action": "buy", "confidence": 0.85, "reasoning": "test"},
    ]
    patched.patch("trader.analyze_news_for_trades", return_value=signals)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert caplog.text.count("max open positions") == 2


def test_zero_positions_allows_buy(patched, caplog):
    patched.patch("trader.get_holdings", return_value={})
    signals = [{"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"}]
    patched.patch("trader.analyze_news_for_trades", return_value=signals)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "max open positions" not in caplog.text.lower()
