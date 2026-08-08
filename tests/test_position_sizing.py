"""Tests for Day 62 — confidence-scaled position sizing.

`trader.size_position` linearly scales trade size between MIN_TRADE_AMOUNT
and MAX_TRADE_AMOUNT over the confidence range [MIN_CONFIDENCE, 1.0] — the
only range that reaches it, since lower-confidence signals are filtered out
upstream. See STRATEGY.md's "Position sizing and confidence math" section.
"""
from __future__ import annotations

import logging
import re

import pytest
import trader


# ── size_position: pure function, no mocking needed ─────────────────────────

def test_higher_confidence_sizes_larger_trade():
    """The literal Day 62 done-when: 0.99 confidence sizes bigger than 0.81,
    both within the configured min/max bounds."""
    lo = trader.size_position(0.81, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    hi = trader.size_position(0.99, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert hi > lo
    assert 1.0 <= lo <= 25.0
    assert 1.0 <= hi <= 25.0


def test_confidence_at_floor_sizes_minimum():
    size = trader.size_position(0.80, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(1.0)


def test_confidence_at_one_sizes_maximum():
    size = trader.size_position(1.0, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(25.0)


def test_confidence_midpoint_sizes_midpoint():
    # min_confidence=0.80, so 0.90 is the midpoint of [0.80, 1.0] -> t=0.5
    size = trader.size_position(0.90, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(13.0)  # 1.0 + 0.5 * (25.0 - 1.0)


def test_confidence_below_floor_clamps_to_minimum():
    size = trader.size_position(0.50, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(1.0)


def test_confidence_above_one_clamps_to_maximum():
    size = trader.size_position(1.5, min_confidence=0.80, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(25.0)


def test_degenerate_span_returns_max_amount():
    # min_confidence == 1.0 means there's no real range to scale over.
    size = trader.size_position(1.0, min_confidence=1.0, min_trade_amount=1.0, max_trade_amount=25.0)
    assert size == pytest.approx(25.0)


def test_min_equals_max_is_flat_regardless_of_confidence():
    size_lo = trader.size_position(0.81, min_confidence=0.80, min_trade_amount=5.0, max_trade_amount=5.0)
    size_hi = trader.size_position(0.99, min_confidence=0.80, min_trade_amount=5.0, max_trade_amount=5.0)
    assert size_lo == size_hi == pytest.approx(5.0)


# ── Integration: confidence flows through a real trading cycle ──────────────

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
    monkeypatch.setenv("MIN_TRADE_AMOUNT", "1.0")
    monkeypatch.setenv("MAX_TRADE_AMOUNT", "25.0")
    monkeypatch.setenv("MIN_CONFIDENCE", "0.80")
    monkeypatch.delenv("BALANCE_ALERT_THRESHOLD", raising=False)
    monkeypatch.delenv("PROFIT_TARGET", raising=False)
    monkeypatch.chdir(tmp_path)

    import config, importlib
    importlib.reload(config)
    mocker.patch("trader.cfg", config.Config.from_env())

    mocker.patch("trader.kill_switch_active", return_value=False)
    mock_client = mocker.patch("trader.get_client").return_value
    mock_client.query_private.return_value = {"result": {"open": {}}}
    mocker.patch("trader.get_balance", return_value=1000.0)  # large enough that balance*0.25 never binds
    mocker.patch("trader.get_holdings", return_value={})
    mocker.patch("trader.get_tradable_coins", return_value=["DOGE", "SHIB"])
    mocker.patch("trader.check_new_listings", return_value=[])
    mocker.patch("trader.find_pumping_coins", return_value=[])
    mocker.patch("trader.fetch_top_headlines", return_value=[
        {"title": "test headline (position_sizing)", "url": "http://test/position-sizing"},
    ])
    mocker.patch("trader.format_headlines_for_prompt", return_value="")
    mocker.patch("trader.get_price", return_value=0.10)
    return mocker


def _logged_amount(caplog_text: str, coin: str) -> float:
    match = re.search(rf"\$([0-9.]+) of {coin}", caplog_text)
    assert match, f"no logged trade amount found for {coin} in:\n{caplog_text}"
    return float(match.group(1))


def test_higher_confidence_signal_sizes_larger_trade_end_to_end(base_patches, caplog):
    mocker = base_patches
    mocker.patch("trader.analyze_news_for_trades", return_value=[
        {"coin": "DOGE", "action": "buy", "confidence": 0.81, "reasoning": "marginal"},
        {"coin": "SHIB", "action": "buy", "confidence": 0.99, "reasoning": "strong"},
    ])
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()

    doge_amount = _logged_amount(caplog.text, "DOGE")
    shib_amount = _logged_amount(caplog.text, "SHIB")

    assert shib_amount > doge_amount
    assert 1.0 <= doge_amount <= 25.0
    assert 1.0 <= shib_amount <= 25.0
