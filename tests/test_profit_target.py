"""Tests for Day 40 — session profit target halt."""
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
def base_patches(mocker, monkeypatch, tmp_path):
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
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=[])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[])
    return mocker


def test_profit_target_halts_cycle(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("PROFIT_TARGET", "30.0")

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    # First cycle sets _starting_balance = 100
    mocker.patch("trader.get_balance", return_value=100.0)
    trader.run_trading_cycle()

    # Second cycle: balance is now 135 → profit = $35, above $30 target
    mocker.patch("trader.get_balance", return_value=135.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "profit target" in caplog.text.lower()


def test_profit_target_not_reached_continues(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("PROFIT_TARGET", "50.0")

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_balance", return_value=100.0)
    trader.run_trading_cycle()

    # Profit = $10, below $50 target — should continue to signal processing
    mocker.patch("trader.get_balance", return_value=110.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "profit target" not in caplog.text.lower()
    assert "trading cycle complete" in caplog.text.lower()


def test_no_profit_target_never_halts(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.delenv("PROFIT_TARGET", raising=False)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_balance", return_value=100.0)
    trader.run_trading_cycle()

    mocker.patch("trader.get_balance", return_value=999.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "profit target" not in caplog.text.lower()
    assert "trading cycle complete" in caplog.text.lower()


def test_profit_target_exact_boundary(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("PROFIT_TARGET", "25.0")

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.get_balance", return_value=100.0)
    trader.run_trading_cycle()

    # Profit = exactly $25 — should halt (>= check)
    mocker.patch("trader.get_balance", return_value=125.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "profit target" in caplog.text.lower()
