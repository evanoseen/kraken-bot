"""Tests for Day 41 — per-coin trade cap."""
from __future__ import annotations

import logging
import pytest
import coin_trade_counter
import trader


@pytest.fixture(autouse=True)
def reset_all():
    coin_trade_counter.reset()
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False
    yield
    coin_trade_counter.reset()
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    trader._balance_alert_sent = False


# ── unit tests for coin_trade_counter module ─────────────────────────────────

def test_increment_and_get_count():
    coin_trade_counter.increment("DOGE")
    coin_trade_counter.increment("DOGE")
    assert coin_trade_counter.get_count("DOGE") == 2


def test_case_insensitive():
    coin_trade_counter.increment("doge")
    assert coin_trade_counter.get_count("DOGE") == 1
    assert coin_trade_counter.at_cap("doge", 1) is True


def test_at_cap_false_below_limit():
    coin_trade_counter.increment("BTC")
    assert coin_trade_counter.at_cap("BTC", 3) is False


def test_at_cap_true_at_limit():
    for _ in range(3):
        coin_trade_counter.increment("BTC")
    assert coin_trade_counter.at_cap("BTC", 3) is True


def test_at_cap_none_never_caps():
    for _ in range(100):
        coin_trade_counter.increment("BTC")
    assert coin_trade_counter.at_cap("BTC", None) is False


def test_reset_clears_all():
    coin_trade_counter.increment("DOGE")
    coin_trade_counter.increment("BTC")
    coin_trade_counter.reset()
    assert coin_trade_counter.get_count("DOGE") == 0
    assert coin_trade_counter.get_count("BTC") == 0


def test_unknown_coin_zero():
    assert coin_trade_counter.get_count("XRP") == 0
    assert coin_trade_counter.at_cap("XRP", 1) is False


# ── integration: capped coin skipped in trading cycle ────────────────────────

@pytest.fixture()
def base_patches(mocker, monkeypatch, tmp_path):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.setenv("MAX_TRADES_PER_COIN", "2")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    return mocker


def test_coin_skipped_when_at_cap(base_patches, caplog):
    # Pre-load the counter to the cap
    coin_trade_counter.increment("DOGE")
    coin_trade_counter.increment("DOGE")

    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "per-coin cap reached" in caplog.text


def test_coin_not_skipped_below_cap(base_patches, caplog):
    coin_trade_counter.increment("DOGE")  # 1 of 2

    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    assert "per-coin cap reached" not in caplog.text
    assert "DOGE" in caplog.text
