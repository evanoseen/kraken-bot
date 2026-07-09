"""Tests for Day 43 — minimum balance reserve."""
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
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)

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


def _reload_cfg(monkeypatch, mocker):
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())


def test_reserve_blocks_when_available_below_min(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "50.0")
    _reload_cfg(monkeypatch, mocker)
    # balance=52, available=2 → below $5 floor
    mocker.patch("trader.get_balance", return_value=52.0)
    with caplog.at_level(logging.WARNING, logger="trader"):
        trader.run_trading_cycle()
    assert "available balance" in caplog.text.lower()
    assert "trading cycle complete" not in caplog.text.lower()


def test_reserve_allows_when_available_above_min(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "50.0")
    _reload_cfg(monkeypatch, mocker)
    # balance=100, available=50 → fine
    mocker.patch("trader.get_balance", return_value=100.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "available balance" not in caplog.text.lower()
    assert "trading cycle complete" in caplog.text.lower()


def test_zero_reserve_no_change(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "0.0")
    _reload_cfg(monkeypatch, mocker)
    mocker.patch("trader.get_balance", return_value=10.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "available balance" not in caplog.text.lower()
    assert "trading cycle complete" in caplog.text.lower()


def test_reserve_default_is_zero(base_patches, monkeypatch):
    mocker = base_patches
    monkeypatch.delenv("MIN_BALANCE_RESERVE", raising=False)
    import config, importlib
    importlib.reload(config)
    cfg = config.Config.from_env()
    assert cfg.min_balance_reserve == 0.0


def test_reserve_exact_boundary_blocks(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "50.0")
    _reload_cfg(monkeypatch, mocker)
    # balance=55, available=5 → exactly at the floor, NOT blocked (>= 5)
    mocker.patch("trader.get_balance", return_value=55.0)
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "available balance" not in caplog.text.lower()
    assert "trading cycle complete" in caplog.text.lower()
