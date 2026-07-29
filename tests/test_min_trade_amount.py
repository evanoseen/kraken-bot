"""Tests for Day 46 — minimum trade amount floor."""
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
    monkeypatch.setenv("MIN_BALANCE_RESERVE", "0")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[
        {"title": "test headline (min_trade_amount)", "url": "http://test/min-trade-amount"},
    ])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.get_price", return_value=0.08)
    return mocker


def _reload(monkeypatch, mocker):
    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())


def test_trade_skipped_below_floor(base_patches, monkeypatch, caplog):
    mocker = base_patches
    # balance=6, available=6, confidence=0.05, max_trade=25 → size=1.25*0.05=1.25 but
    # available*0.25=1.50 → trade_amount=min(25*0.05, 6*0.25)=min(1.25,1.5)=1.25
    # Set MIN_TRADE_AMOUNT=5 so 1.25 is below floor
    monkeypatch.setenv("MIN_TRADE_AMOUNT", "5.0")
    monkeypatch.setenv("MAX_TRADE_AMOUNT", "25.0")
    _reload(monkeypatch, mocker)
    mocker.patch("trader.get_balance", return_value=6.0)
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.05, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "below minimum" in caplog.text


def test_trade_proceeds_above_floor(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("MIN_TRADE_AMOUNT", "1.0")
    monkeypatch.setenv("MAX_TRADE_AMOUNT", "25.0")
    _reload(monkeypatch, mocker)
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "below minimum" not in caplog.text
    assert "DOGE" in caplog.text


def test_default_floor_is_one_cad(monkeypatch):
    monkeypatch.delenv("MIN_TRADE_AMOUNT", raising=False)
    import config, importlib
    importlib.reload(config)
    assert config.Config.from_env().min_trade_amount == 1.0


def test_exact_boundary_not_skipped(base_patches, monkeypatch, caplog):
    mocker = base_patches
    # Set floor=5, and construct a scenario where trade_amount==5 exactly → should NOT skip
    monkeypatch.setenv("MIN_TRADE_AMOUNT", "5.0")
    monkeypatch.setenv("MAX_TRADE_AMOUNT", "5.0")
    _reload(monkeypatch, mocker)
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 1.0, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "below minimum" not in caplog.text
