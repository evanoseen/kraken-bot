"""Unit tests for `news_fetcher.fetch_top_headlines` and helpers.

The function blends RSS feeds with Twitter/Nitter pulls. These tests mock
`feedparser.parse` so no network calls fire and stub
`fetch_twitter_signals` to keep RSS-only behavior isolated.

Three required cases per the Day 11 backlog: happy path, no-title skip,
dedupe. Code dedupes by **title** (not link as the backlog originally
assumed); the tests pin the actual behavior.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────


def _fake_feed(entries: list[dict]) -> MagicMock:
    """Return a MagicMock shaped like `feedparser.parse(...)`'s return value.

    `feedparser` returns an object whose `.entries` is a list. Each entry
    exposes `.get(key, default)` like a dict; using a real dict is the
    simplest faithful stand-in.
    """
    feed = MagicMock()
    feed.entries = entries
    return feed


@pytest.fixture
def patched_news_fetcher(mocker):
    """Import `news_fetcher` with `feedparser.parse` and the Twitter path patched.

    By default `feedparser.parse` returns an empty feed for every URL.
    Tests override `mock_parse.side_effect` per-call to inject feed shapes.
    `fetch_twitter_signals` is stubbed to `[]` so RSS-only behavior is
    isolated from the 150+ Nitter URL calls in the real implementation.
    """
    import news_fetcher

    mock_parse = mocker.patch("news_fetcher.feedparser.parse", return_value=_fake_feed([]))
    mocker.patch.object(news_fetcher, "fetch_twitter_signals", return_value=[])

    return news_fetcher, mock_parse


# ─── Tests ────────────────────────────────────────────────────────────────


def test_happy_path_returns_shaped_articles(patched_news_fetcher):
    """A normal RSS response is converted into dicts with title/summary/source."""
    nf, mock_parse = patched_news_fetcher

    # Same feed returned for every RSS_FEEDS[:6] call; dedup means we still
    # only get the unique entries below.
    mock_parse.return_value = _fake_feed([
        {"title": "Elon Musk tweets DOGE to the moon", "summary": "summary one"},
        {"title": "Kraken lists new meme coin XYZ", "summary": "summary two"},
        {"title": "Bitcoin breaks $100k for first time", "summary": "summary three"},
    ])

    articles = nf.fetch_top_headlines(max_articles=60)

    assert len(articles) == 3
    for a in articles:
        assert set(a.keys()) >= {"title", "summary", "source"}
        assert a["source"] == "news"
        assert a["title"]


def test_entries_without_title_are_skipped(patched_news_fetcher):
    """An entry whose `title` is empty/missing is filtered out."""
    nf, mock_parse = patched_news_fetcher

    mock_parse.return_value = _fake_feed([
        {"title": "Real headline", "summary": "ok"},
        {"title": "", "summary": "empty title — should be skipped"},
        {"summary": "no title key at all — should be skipped"},
        {"title": "Another real headline", "summary": "ok"},
    ])

    articles = nf.fetch_top_headlines(max_articles=60)

    titles = [a["title"] for a in articles]
    assert "Real headline" in titles
    assert "Another real headline" in titles
    assert "" not in titles
    assert len(articles) == 2


def test_dedupes_by_title_across_feeds(patched_news_fetcher):
    """The same headline appearing on every feed appears once in the output."""
    nf, mock_parse = patched_news_fetcher

    # Every RSS feed returns the same single-entry list. The function calls
    # feedparser.parse six times (RSS_FEEDS[:6]); without dedup we'd see 6
    # copies. With dedup-by-title we should see 1.
    mock_parse.return_value = _fake_feed([
        {"title": "Same headline everywhere", "summary": "syndicated"},
    ])

    articles = nf.fetch_top_headlines(max_articles=60)

    assert len(articles) == 1
    assert articles[0]["title"] == "Same headline everywhere"


def test_max_articles_cap_is_respected(patched_news_fetcher):
    """The `max_articles` parameter truncates the output list."""
    nf, mock_parse = patched_news_fetcher

    # 20 unique entries; cap to 5.
    entries = [{"title": f"Headline {i}", "summary": f"s{i}"} for i in range(20)]
    mock_parse.return_value = _fake_feed(entries)

    articles = nf.fetch_top_headlines(max_articles=5)

    assert len(articles) == 5


def test_format_headlines_for_prompt_uses_emoji_prefixes():
    """The formatter prefixes news with 📰 and tweets with 🐦."""
    import news_fetcher as nf

    articles = [
        {"title": "RSS headline A", "source": "news"},
        {"title": "[TWEET @elonmusk] DOGE rocket", "source": "twitter"},
        {"title": "RSS headline B", "source": "news"},
    ]

    prompt = nf.format_headlines_for_prompt(articles)

    lines = prompt.split("\n")
    assert lines[0].startswith("1. 📰")
    assert lines[1].startswith("2. 🐦")
    assert lines[2].startswith("3. 📰")
    assert "RSS headline A" in lines[0]
    assert "DOGE rocket" in lines[1]


def test_feedparser_exception_does_not_crash(patched_news_fetcher):
    """If one feed raises, the function continues with whatever it got."""
    nf, mock_parse = patched_news_fetcher

    # First call raises, subsequent calls return one entry each.
    good_feed = _fake_feed([{"title": "Survivor headline", "summary": "ok"}])
    mock_parse.side_effect = [
        RuntimeError("simulated RSS failure"),
        good_feed, good_feed, good_feed, good_feed, good_feed,
    ]

    articles = nf.fetch_top_headlines(max_articles=60)

    # At least the survivor came through; no exception escaped.
    titles = [a["title"] for a in articles]
    assert "Survivor headline" in titles
