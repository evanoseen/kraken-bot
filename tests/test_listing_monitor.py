"""Tests for listing_monitor.check_new_listings (Day 77).

check_new_listings had zero direct unit tests before this — every mention
of it elsewhere in the suite mocks it out entirely. These mock
feedparser.parse and sandbox seen_listings.json into tmp_path (via
monkeypatch.chdir) to cover a watchlist match, a non-watchlist listing,
an already-seen entry, and the seen-file persistence round-trip.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import listing_monitor
from listing_monitor import WATCHLIST, check_new_listings


def _entry(title: str, entry_id: str = None, link: str = None) -> dict:
    d = {"title": title}
    if entry_id is not None:
        d["id"] = entry_id
    if link is not None:
        d["link"] = link
    return d


def _feed(entries: list[dict]) -> MagicMock:
    feed = MagicMock()
    feed.entries = entries
    return feed


@pytest.fixture(autouse=True)
def sandbox_seen_file(monkeypatch, tmp_path):
    """seen_listings.json is a bare relative filename — sandbox it per test."""
    monkeypatch.chdir(tmp_path)


def test_watchlist_match_returns_coin(mocker):
    coin = next(iter(WATCHLIST))
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coin} NOW AVAILABLE for trading", entry_id="e1"),
    ]))
    result = check_new_listings()
    assert result == [coin]


def test_non_watchlist_listing_is_logged_not_bought(mocker, caplog):
    import logging
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry("RANDOMCOIN LISTING announced", entry_id="e1"),
    ]))
    with caplog.at_level(logging.INFO, logger="listing_monitor"):
        result = check_new_listings()
    assert result == []
    assert "New Kraken listing" in caplog.text


def test_already_seen_entry_is_skipped(mocker):
    coin = next(iter(WATCHLIST))
    listing_monitor.save_seen({"e1"})

    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coin} NOW AVAILABLE", entry_id="e1"),
    ]))
    result = check_new_listings()
    assert result == []


def test_non_listing_entry_is_ignored_and_not_marked_seen(mocker):
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry("Just a regular blog post about crypto trends", entry_id="e1"),
    ]))
    result = check_new_listings()
    assert result == []
    assert listing_monitor.load_seen() == set()


def test_seen_file_persists_across_calls(mocker):
    """The literal Day 77 done-when: seen_listings.json round-trips so the
    same entry never fires twice, even across separate check_new_listings()
    invocations (as would happen across real trading cycles)."""
    coin = next(iter(WATCHLIST))
    mock_parse = mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coin} NOW AVAILABLE", entry_id="e1"),
    ]))

    first = check_new_listings()
    assert first == [coin]

    # Same entry, second call — already marked seen, must not fire again.
    second = check_new_listings()
    assert second == []

    assert mock_parse.call_count == 2
    assert "e1" in listing_monitor.load_seen()


def test_seen_file_written_as_json_list(mocker):
    coin = next(iter(WATCHLIST))
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coin} NOW AVAILABLE", entry_id="e1"),
    ]))
    check_new_listings()

    with open(listing_monitor.SEEN_FILE) as f:
        data = json.load(f)
    assert data == ["e1"]


def test_entry_without_id_falls_back_to_link(mocker):
    coin = next(iter(WATCHLIST))
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coin} NOW AVAILABLE", link="https://blog.kraken.com/post/1"),
    ]))
    check_new_listings()
    assert "https://blog.kraken.com/post/1" in listing_monitor.load_seen()


def test_multiple_watchlist_mentions_yields_exactly_one_coin(mocker):
    coins = list(WATCHLIST)[:2]
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coins[0]} and {coins[1]} NOW AVAILABLE", entry_id="e1"),
    ]))
    result = check_new_listings()
    assert len(result) == 1
    assert result[0] in coins


def test_feedparser_exception_is_caught_returns_empty(mocker):
    mocker.patch("listing_monitor.feedparser.parse", side_effect=RuntimeError("feed unreachable"))
    result = check_new_listings()
    assert result == []


def test_only_first_20_entries_are_considered(mocker):
    coin = next(iter(WATCHLIST))
    # 25 non-matching entries, then a matching one at index 22 — past the cap.
    entries = [_entry(f"Filler post {i}", entry_id=f"filler{i}") for i in range(22)]
    entries.append(_entry(f"{coin} NOW AVAILABLE", entry_id="late"))
    entries += [_entry(f"Filler post {i}", entry_id=f"filler{i}") for i in range(22, 24)]
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed(entries))
    result = check_new_listings()
    assert result == []


def test_multiple_new_listing_entries_in_one_cycle(mocker):
    coins = list(WATCHLIST)[:2]
    mocker.patch("listing_monitor.feedparser.parse", return_value=_feed([
        _entry(f"{coins[0]} NOW AVAILABLE", entry_id="e1"),
        _entry(f"{coins[1]} LAUNCHES today", entry_id="e2"),
    ]))
    result = check_new_listings()
    assert sorted(result) == sorted(coins)
