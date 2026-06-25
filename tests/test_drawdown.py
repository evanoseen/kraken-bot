"""Tests for Day 27 drawdown circuit breaker."""
from __future__ import annotations

import os
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
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.20")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.chdir(tmp_path)

    import config
    import importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mocker.patch("trader.get_client")
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    mock_balance = mocker.patch("trader.get_balance")
    return mock_balance


def test_peak_balance_tracked(patched):
    patched.return_value = 100.0
    trader.run_trading_cycle()
    assert trader._peak_balance == 100.0


def test_peak_updates_on_gain(patched):
    patched.return_value = 100.0
    trader.run_trading_cycle()
    patched.return_value = 120.0
    trader.run_trading_cycle()
    assert trader._peak_balance == 120.0


def test_peak_does_not_drop_on_loss(patched):
    patched.return_value = 100.0
    trader.run_trading_cycle()
    patched.return_value = 90.0
    trader.run_trading_cycle()
    assert trader._peak_balance == 100.0


def test_circuit_breaker_fires_at_threshold(patched, caplog, mocker):
    import logging
    patched.return_value = 100.0
    trader.run_trading_cycle()
    patched.return_value = 79.0  # 21% drawdown > 20% threshold
    analyze = mocker.patch("trader.analyze_news_for_trades", return_value=[])
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "circuit breaker" in caplog.text.lower()
    analyze.assert_not_called()


def test_circuit_breaker_does_not_fire_below_threshold(patched, mocker):
    patched.return_value = 100.0
    trader.run_trading_cycle()
    patched.return_value = 85.0  # 15% drawdown < 20% threshold
    analyze = mocker.patch("trader.analyze_news_for_trades", return_value=[])
    trader.run_trading_cycle()
    analyze.assert_called_once()
