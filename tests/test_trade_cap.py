"""Tests for Day 34 — daily trade cap."""
from __future__ import annotations

import logging
import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    yield
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0


@pytest.fixture()
def patched(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "3")
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
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    return mocker


def test_cycle_runs_under_cap(patched):
    trader._trades_today = 2
    trader.run_trading_cycle()
    trader.analyze_news_for_trades.assert_called_once()


def test_cycle_halts_at_cap(patched, caplog):
    trader._trades_today = 3
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "daily trade cap" in caplog.text.lower()
    trader.analyze_news_for_trades.assert_not_called()


def test_cycle_halts_above_cap(patched, caplog):
    trader._trades_today = 10
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "daily trade cap" in caplog.text.lower()


def test_cap_message_shows_count(patched, caplog):
    trader._trades_today = 3
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "3/3" in caplog.text
