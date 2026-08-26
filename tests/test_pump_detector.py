"""Tests for pump_detector.find_pumping_coins (Day 77).

find_pumping_coins had zero direct unit tests before this — every mention
of it elsewhere in the suite mocks it out entirely. These mock the Kraken
client's query_public responses directly to cover the actual spike math,
IGNORE_COINS filtering, the $5M daily-volume ceiling, and the malformed-
ticker guards.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from pump_detector import IGNORE_COINS, find_pumping_coins


def _ticker(volume_today, volume_24h, price, low_24h, high_24h=None, trades_today=10):
    return {
        "v": [str(volume_today), str(volume_24h)],
        "c": [str(price), "0"],
        "l": ["0", str(low_24h)],
        "h": ["0", str(high_24h if high_24h is not None else price)],
        "t": [trades_today, trades_today * 5],
    }


def _client(pairs: dict, tickers: dict, ticker_error=None, pairs_error=None) -> MagicMock:
    """A Mock krakenex client whose query_public("Ticker"/"AssetPairs")
    returns the given canned responses, keyed by endpoint name."""
    client = MagicMock()

    def query_public(endpoint):
        if endpoint == "Ticker":
            if ticker_error:
                return {"error": [ticker_error]}
            return {"result": tickers}
        if endpoint == "AssetPairs":
            if pairs_error:
                return {"error": [pairs_error]}
            return {"result": pairs}
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    client.query_public.side_effect = query_public
    return client


# ── Error handling ───────────────────────────────────────────────────────

def test_ticker_error_returns_empty():
    client = _client({}, {}, ticker_error="EGeneral:Unavailable")
    assert find_pumping_coins(client) == []


def test_asset_pairs_error_returns_empty():
    client = _client({}, {}, pairs_error="EGeneral:Unavailable")
    assert find_pumping_coins(client) == []


def test_no_candidates_returns_empty():
    client = _client({}, {})
    assert find_pumping_coins(client) == []


# ── Happy path: a qualifying obscure coin ───────────────────────────────

def test_qualifying_coin_is_returned_with_correct_fields():
    pairs = {"FOOCAD": {"base": "XFOO", "quote": "ZCAD"}}
    tickers = {"FOOCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)

    results = find_pumping_coins(client, min_volume_multiplier=2.0)

    assert len(results) == 1
    r = results[0]
    assert r["coin"] == "FOO"
    assert r["pair"] == "FOOCAD"
    assert r["price"] == 1.0
    # avg_hourly = 240/24 = 10, spike = 1000/10 = 100.0x
    assert r["volume_spike"] == 100.0
    # (1.0 - 0.9) / 0.9 * 100 = 11.1%
    assert r["price_change_24h"] == pytest.approx(11.1, abs=0.1)
    assert r["daily_volume_usd"] == 240.0  # volume_24h * price
    assert r["trades_today"] == 10


def test_double_x_prefix_strips_both_leading_x_characters():
    # lstrip("X") strips EVERY leading X, not just one occurrence — Kraken's
    # real asset codes use exactly this variable-length X-prefixing (e.g.
    # "XXDG" for DOGE has two leading X's, "XETH" for ETH has one).
    pairs = {"DGCAD": {"base": "XXDG", "quote": "ZCAD"}}
    tickers = {"DGCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    results = find_pumping_coins(client)
    assert results[0]["coin"] == "DG"


# ── IGNORE_COINS filtering ───────────────────────────────────────────────

@pytest.mark.parametrize("coin", ["BTC", "DOGE", "USDT", "BODEN"])
def test_ignore_coins_are_filtered_even_if_otherwise_qualifying(coin):
    base = "X" + coin
    pairs = {"PAIRCAD": {"base": base, "quote": "ZCAD"}}
    tickers = {"PAIRCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_ignore_coins_set_contains_known_categories():
    # Majors, stablecoins, popular memes, and Ontario geo-blocked tickers.
    assert {"BTC", "ETH", "USDT", "DOGE", "SHIB", "BODEN"} <= IGNORE_COINS


# ── $5M daily volume ceiling ─────────────────────────────────────────────

def test_high_daily_volume_coin_is_excluded():
    pairs = {"BIGCAD": {"base": "XBIG", "quote": "ZCAD"}}
    # volume_24h * price = 10_000_000 * 1.0 = $10M/day — over the $5M ceiling
    tickers = {"BIGCAD": _ticker(volume_today=100_000_000, volume_24h=10_000_000, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_just_under_daily_volume_ceiling_is_included():
    pairs = {"OKCAD": {"base": "XOK", "quote": "ZCAD"}}
    # 4_999_999 * 1.0 < $5M
    tickers = {"OKCAD": _ticker(volume_today=100_000_000, volume_24h=4_999_999, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    results = find_pumping_coins(client)
    assert len(results) == 1
    assert results[0]["coin"] == "OK"


# ── Non-CAD quote pairs are excluded entirely ───────────────────────────

def test_non_cad_quote_pair_is_excluded():
    pairs = {"BAZUSD": {"base": "XBAZ", "quote": "ZUSD"}}
    tickers = {"BAZUSD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_cad_literal_quote_is_accepted_alongside_zcad():
    pairs = {"QUXCAD": {"base": "XQUX", "quote": "CAD"}}
    tickers = {"QUXCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    results = find_pumping_coins(client)
    assert len(results) == 1


# ── Malformed / missing ticker data doesn't crash the scan ──────────────

def test_malformed_ticker_is_skipped_not_crashed():
    pairs = {
        "BADCAD": {"base": "XBAD", "quote": "ZCAD"},
        "GOODCAD": {"base": "XGOOD", "quote": "ZCAD"},
    }
    tickers = {
        "BADCAD": {"v": ["not-a-number", "1"], "c": ["1"], "l": ["0", "1"], "h": ["0", "1"], "t": [1]},
        "GOODCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.9),
    }
    client = _client(pairs, tickers)
    results = find_pumping_coins(client)
    assert len(results) == 1
    assert results[0]["coin"] == "GOOD"


def test_missing_ticker_keys_is_skipped_not_crashed():
    pairs = {"MISSINGCAD": {"base": "XMISSING", "quote": "ZCAD"}}
    tickers = {"MISSINGCAD": {"v": ["100"]}}  # missing "c", "l", "h", "t"
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_zero_volume_24h_is_skipped():
    pairs = {"DEADCAD": {"base": "XDEAD", "quote": "ZCAD"}}
    tickers = {"DEADCAD": _ticker(volume_today=0, volume_24h=0, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_zero_price_is_skipped():
    pairs = {"FREECAD": {"base": "XFREE", "quote": "ZCAD"}}
    tickers = {"FREECAD": _ticker(volume_today=1000, volume_24h=240, price=0.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_zero_low_24h_treats_price_change_as_zero_not_crash():
    pairs = {"NOLOWCAD": {"base": "XNOLOW", "quote": "ZCAD"}}
    tickers = {"NOLOWCAD": _ticker(volume_today=1000, volume_24h=240, price=1.0, low_24h=0.0)}
    client = _client(pairs, tickers)
    # price_change_pct falls back to 0, which fails the >1.0 requirement.
    assert find_pumping_coins(client) == []


# ── Spike ratio / price-move thresholds ──────────────────────────────────

def test_spike_below_multiplier_is_excluded():
    pairs = {"SLOWCAD": {"base": "XSLOW", "quote": "ZCAD"}}
    # avg_hourly = 240/24 = 10, spike = 15/10 = 1.5x < default 2.0x minimum
    tickers = {"SLOWCAD": _ticker(volume_today=15, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_price_not_moved_is_excluded_despite_volume_spike():
    pairs = {"FLATCAD": {"base": "XFLAT", "quote": "ZCAD"}}
    # Huge spike, but price barely off the low (<=1%)
    tickers = {"FLATCAD": _ticker(volume_today=10_000, volume_24h=240, price=1.0, low_24h=0.995)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client) == []


def test_custom_min_volume_multiplier_is_respected():
    pairs = {"MEDCAD": {"base": "XMED", "quote": "ZCAD"}}
    # spike = 50/10 = 5.0x
    tickers = {"MEDCAD": _ticker(volume_today=50, volume_24h=240, price=1.0, low_24h=0.9)}
    client = _client(pairs, tickers)
    assert find_pumping_coins(client, min_volume_multiplier=10.0) == []
    assert len(find_pumping_coins(client, min_volume_multiplier=4.0)) == 1


# ── Sorting and top_n ────────────────────────────────────────────────────

def test_results_sorted_by_spike_descending():
    pairs = {
        "LOWCAD": {"base": "XLOW", "quote": "ZCAD"},
        "HIGHCAD": {"base": "XHIGH", "quote": "ZCAD"},
    }
    tickers = {
        "LOWCAD": _ticker(volume_today=30, volume_24h=240, price=1.0, low_24h=0.9),   # 3.0x
        "HIGHCAD": _ticker(volume_today=100, volume_24h=240, price=1.0, low_24h=0.9),  # 10.0x
    }
    client = _client(pairs, tickers)
    results = find_pumping_coins(client)
    assert [r["coin"] for r in results] == ["HIGH", "LOW"]


def test_top_n_limits_result_count():
    pairs = {}
    tickers = {}
    for i in range(8):
        pair = f"COIN{i}CAD"
        pairs[pair] = {"base": f"XCOIN{i}", "quote": "ZCAD"}
        # increasing spikes so ordering is deterministic
        tickers[pair] = _ticker(volume_today=(i + 1) * 10, volume_24h=240, price=1.0, low_24h=0.9)
    client = _client(pairs, tickers)
    results = find_pumping_coins(client, top_n=3)
    assert len(results) == 3
    # highest spikes (COIN7, COIN6, COIN5) win
    assert [r["coin"] for r in results] == ["COIN7", "COIN6", "COIN5"]
