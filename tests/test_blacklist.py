"""Tests for Day 39 — coin blacklist."""
from __future__ import annotations

import logging
import pytest
import trader
import blacklist


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


# ── blacklist module unit tests ──────────────────────────────────────────────

def test_is_blacklisted_true(monkeypatch):
    monkeypatch.setenv("COIN_BLACKLIST", "DOGE,SHIB")
    assert blacklist.is_blacklisted("DOGE") is True
    assert blacklist.is_blacklisted("doge") is True
    assert blacklist.is_blacklisted("SHIB") is True


def test_is_blacklisted_false(monkeypatch):
    monkeypatch.setenv("COIN_BLACKLIST", "DOGE,SHIB")
    assert blacklist.is_blacklisted("BTC") is False


def test_empty_blacklist_allows_all(monkeypatch):
    monkeypatch.setenv("COIN_BLACKLIST", "")
    assert blacklist.is_blacklisted("DOGE") is False
    assert blacklist.is_blacklisted("BTC") is False


def test_unset_blacklist_allows_all(monkeypatch):
    monkeypatch.delenv("COIN_BLACKLIST", raising=False)
    assert blacklist.is_blacklisted("DOGE") is False


def test_get_blacklist_returns_frozenset(monkeypatch):
    monkeypatch.setenv("COIN_BLACKLIST", "doge, shib , xrp")
    bl = blacklist.get_blacklist()
    assert isinstance(bl, frozenset)
    assert bl == {"DOGE", "SHIB", "XRP"}


# ── integration: blacklisted coin is skipped in trading cycle ─────────────

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
    mocker.patch("trader.get_balance", return_value=100.0)
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE", "BTC"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[
        {"title": "test headline (blacklist)", "url": "http://test/blacklist"},
    ])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.get_price", return_value=0.1)
    return mocker


def test_blacklisted_coin_skipped_in_cycle(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("COIN_BLACKLIST", "DOGE")
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "blacklisted" in caplog.text.lower()


def test_non_blacklisted_coin_not_skipped(base_patches, monkeypatch, caplog):
    mocker = base_patches
    monkeypatch.setenv("COIN_BLACKLIST", "DOGE")
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "BTC", "action": "buy", "confidence": 0.9, "reasoning": "test"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert "blacklisted" not in caplog.text.lower()
    assert "BTC" in caplog.text
