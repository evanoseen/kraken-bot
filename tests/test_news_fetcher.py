"""Unit tests for `news_fetcher.fetch_top_headlines` and helpers.

The function blends RSS feeds with Twitter/Nitter pulls. These tests mock
`feedparser.parse` so no network calls fire and stub
`fetch_twitter_signals` to keep RSS-only behavior isolated.

Three required cases per the Day 11 backlog: happy path, no-title skip,
dedupe. Code dedupes by **title** (not link as the backlog originally
assumed); the tests pin the actual behavior.
"""
from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


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

    # Same feed returned for every RSS_FEEDS call; dedup means we still
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
    # feedparser.parse once per RSS_FEEDS entry (six, currently); without
    # dedup we'd see 6 copies. With dedup-by-title we should see 1.
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


def test_every_rss_feed_entry_is_actually_fetched(patched_news_fetcher):
    """`fetch_top_headlines` must request every URL in `RSS_FEEDS`, not a
    stale prefix of it.

    Day 130 regression: `RSS_FEEDS` used to carry 7 appended Nitter URLs
    that a hardcoded `RSS_FEEDS[:6]` slice silently never fetched. This
    pins the loop to the live list itself so a future append can't go
    unread the same way again without this test catching it.
    """
    nf, mock_parse = patched_news_fetcher

    nf.fetch_top_headlines(max_articles=60)

    requested_urls = [call.args[0] for call in mock_parse.call_args_list]
    assert requested_urls == nf.RSS_FEEDS


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


# ─── Day 70: Nitter 3-instance failover in fetch_twitter_signals ───────────
#
# Every test above stubs fetch_twitter_signals to [] — the failover path
# across NITTER_INSTANCES has never actually been exercised. These tests
# call fetch_twitter_signals directly, patching TWITTER_ACCOUNTS to a short
# fixed list (real code loops over ~50 accounts, which would need a mocked
# response per account per instance) and feedparser.parse to a URL-aware
# side_effect that simulates a specific instance being down.


def test_single_instance_failure_falls_through(mocker):
    """First Nitter instance raises; the second one has the headline."""
    import news_fetcher as nf
    mocker.patch.object(nf, "TWITTER_ACCOUNTS", ["testuser"])

    def fake_parse(url):
        if "nitter.poast.org" in url:
            raise ConnectionError("simulated instance down")
        if "nitter.privacydev.net" in url:
            return _fake_feed([{"title": "Fallback headline from second instance", "summary": ""}])
        raise AssertionError(f"should not reach third instance: {url}")

    mocker.patch("news_fetcher.feedparser.parse", side_effect=fake_parse)

    articles = nf.fetch_twitter_signals()

    assert len(articles) == 1
    assert "Fallback headline from second instance" in articles[0]["title"]
    assert articles[0]["source"] == "twitter"


def test_cascading_failure_falls_through_to_third_instance(mocker):
    """First two instances down (timeout, connection error); third survives."""
    import news_fetcher as nf
    mocker.patch.object(nf, "TWITTER_ACCOUNTS", ["testuser"])

    def fake_parse(url):
        if "nitter.poast.org" in url:
            raise TimeoutError("simulated timeout")
        if "nitter.privacydev.net" in url:
            raise ConnectionError("simulated 5xx-like failure")
        if "nitter.1d4.us" in url:
            return _fake_feed([{"title": "Third instance survivor headline", "summary": ""}])
        raise AssertionError(f"unexpected url: {url}")

    mocker.patch("news_fetcher.feedparser.parse", side_effect=fake_parse)

    articles = nf.fetch_twitter_signals()

    assert len(articles) == 1
    assert "Third instance survivor headline" in articles[0]["title"]


def test_empty_entries_without_exception_also_falls_through(mocker):
    """An instance that responds with zero entries (no exception) is
    treated the same as a failure — falls through to the next instance."""
    import news_fetcher as nf
    mocker.patch.object(nf, "TWITTER_ACCOUNTS", ["testuser"])

    def fake_parse(url):
        if "nitter.poast.org" in url:
            return _fake_feed([])  # responds, but nothing there
        if "nitter.privacydev.net" in url:
            return _fake_feed([{"title": "Second instance had actual content", "summary": ""}])
        raise AssertionError(f"should not reach third instance: {url}")

    mocker.patch("news_fetcher.feedparser.parse", side_effect=fake_parse)

    articles = nf.fetch_twitter_signals()

    assert len(articles) == 1
    assert "Second instance had actual content" in articles[0]["title"]


def test_all_instances_down_for_one_account_degrades_gracefully(mocker, caplog):
    """One account's all three instances fail; a second account still
    comes through, and nothing crashes."""
    import logging
    import news_fetcher as nf
    mocker.patch.object(nf, "TWITTER_ACCOUNTS", ["deadaccount", "goodaccount"])

    def fake_parse(url):
        if "deadaccount" in url:
            raise ConnectionError("simulated total outage for this account")
        if "goodaccount" in url and "nitter.poast.org" in url:
            return _fake_feed([{"title": "Good account headline survives", "summary": ""}])
        raise AssertionError(f"unexpected url: {url}")

    mocker.patch("news_fetcher.feedparser.parse", side_effect=fake_parse)

    with caplog.at_level(logging.DEBUG, logger="news_fetcher"):
        articles = nf.fetch_twitter_signals()

    assert len(articles) == 1
    assert "Good account headline survives" in articles[0]["title"]
    assert "deadaccount" in caplog.text


def test_all_accounts_all_instances_down_returns_empty(mocker):
    """Total Nitter outage across every instance and every account degrades
    to an empty list — it must not crash or raise."""
    import news_fetcher as nf
    mocker.patch.object(nf, "TWITTER_ACCOUNTS", ["acct1", "acct2"])
    mocker.patch("news_fetcher.feedparser.parse", side_effect=ConnectionError("simulated total nitter outage"))

    articles = nf.fetch_twitter_signals()

    assert articles == []


# ─── Day 131: "~50 high-signal accounts" ceiling claim vs. real TWITTER_ACCOUNTS ──
#
# STRATEGY.md ("Up to ~50 high-signal accounts on X via Nitter RSS") and
# news_fetcher.py's own module docstring ("~50 high-signal X accounts") both
# state an approximate *ceiling*, not an exact count — TWITTER_ACCOUNTS
# currently holds 41 entries (Day 130's own finding while fixing the
# unrelated RSS_FEEDS dead-code bug). Unlike README's test-count claims
# (tests/test_readme_test_count.py) or ISA.md's ISC-19 field count
# (tests/test_status.py), "~N" is a stated ceiling, so the lock here is an
# inequality, not an equality: a future account addition that pushes the
# real count past what the docs promise should fail loudly instead of
# sitting unnoticed the way the Day 130 RSS_FEEDS entries did.

CEILING_PATTERN = re.compile(r"~(\d+) high-signal")


def _claimed_account_ceilings() -> list[int]:
    """Every "~N high-signal" ceiling claim across STRATEGY.md and
    news_fetcher.py's own module docstring."""
    import news_fetcher as nf

    strategy_text = (REPO_ROOT / "STRATEGY.md").read_text()
    docstring_text = Path(nf.__file__).read_text()
    return [int(n) for n in CEILING_PATTERN.findall(strategy_text + docstring_text)]


def test_twitter_accounts_count_does_not_exceed_claimed_ceiling():
    """The real `TWITTER_ACCOUNTS` list must never grow past the "~N
    high-signal accounts" ceiling STRATEGY.md and news_fetcher.py's
    docstring both state."""
    import news_fetcher as nf

    ceilings = _claimed_account_ceilings()
    assert ceilings, (
        "Expected at least one '~N high-signal' ceiling claim in "
        "STRATEGY.md and news_fetcher.py's module docstring"
    )

    real_count = len(nf.TWITTER_ACCOUNTS)
    exceeded = [c for c in ceilings if real_count > c]
    assert not exceeded, (
        f"TWITTER_ACCOUNTS has grown to {real_count} entries, exceeding the "
        f"claimed ceiling(s) {exceeded} in STRATEGY.md/news_fetcher.py's "
        f"docstring — update the doc wording (or trim the list) to match."
    )
