"""Tests for Day 47 — news headline dedup cache."""
from __future__ import annotations

import logging
import pytest
import headline_cache
import trader


@pytest.fixture(autouse=True)
def reset_cache():
    headline_cache.reset()
    yield
    headline_cache.reset()


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


# ── unit tests ───────────────────────────────────────────────────────────────

A1 = {"url": "https://example.com/a", "title": "Article A"}
A2 = {"url": "https://example.com/b", "title": "Article B"}
A3 = {"title": "Article C (no url)"}


def test_all_new_when_cache_empty():
    result = headline_cache.filter_new([A1, A2])
    assert result == [A1, A2]


def test_seen_articles_filtered():
    headline_cache.mark_seen([A1])
    result = headline_cache.filter_new([A1, A2])
    assert result == [A2]


def test_all_filtered_when_all_seen():
    headline_cache.mark_seen([A1, A2])
    assert headline_cache.filter_new([A1, A2]) == []


def test_url_takes_priority_over_title():
    headline_cache.mark_seen([A1])
    # Same URL, different title — should still be filtered
    duplicate = {"url": "https://example.com/a", "title": "Different title"}
    assert headline_cache.filter_new([duplicate]) == []


def test_title_used_when_no_url():
    headline_cache.mark_seen([A3])
    assert headline_cache.filter_new([A3]) == []


def test_article_missing_both_always_passes():
    empty = {}
    result = headline_cache.filter_new([empty])
    assert result == [empty]


def test_mark_seen_does_not_add_keyless():
    headline_cache.mark_seen([{}])
    # Nothing in cache — keyless article is still "new" next time
    assert headline_cache.filter_new([{}]) == [{}]


def test_reset_clears_cache():
    headline_cache.mark_seen([A1, A2])
    headline_cache.reset()
    assert headline_cache.filter_new([A1, A2]) == [A1, A2]


# ── integration: second cycle skips Claude when headlines repeat ─────────────

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
    mocker.patch("trader.format_headlines_for_prompt", return_value="headline text")
    return mocker


def test_claude_skipped_on_repeat_headlines(base_patches, caplog):
    mocker = base_patches
    articles = [{"url": "https://news.example.com/1", "title": "Big crypto news"}]
    mocker.patch("trader.fetch_top_headlines", return_value=articles)
    analyze = mocker.patch("trader.analyze_news_for_trades", return_value=[])

    trader.run_trading_cycle()
    assert analyze.call_count == 1

    # Second cycle — same articles, Claude should NOT be called again
    with caplog.at_level(logging.INFO, logger="trader"):
        trader.run_trading_cycle()
    assert analyze.call_count == 1
    assert "skipping claude" in caplog.text.lower()


def test_claude_called_on_new_headlines(base_patches):
    mocker = base_patches
    mocker.patch("trader.fetch_top_headlines", side_effect=[
        [{"url": "https://news.example.com/1", "title": "Story one"}],
        [{"url": "https://news.example.com/2", "title": "Story two"}],
    ])
    analyze = mocker.patch("trader.analyze_news_for_trades", return_value=[])

    trader.run_trading_cycle()
    trader.run_trading_cycle()
    assert analyze.call_count == 2
