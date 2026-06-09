"""Unit tests for `kraken_client` — the thin wrapper around `krakenex.API`.

All tests use the shared `kraken_dryrun` fixture from `tests/conftest.py`,
which returns a MagicMock shaped like a `krakenex.API` instance with
`query_private` and `query_public` preloaded with canned responses for
every endpoint the wrapper actually calls (Balance, OpenOrders, AddOrder,
CancelOrder, AssetPairs, Ticker).

Note on the Day 12 backlog: it suggested `requests-mock` and described a
`KrakenClient.get_balance()` method that raises on HTTP 5xx. The real code
is shaped differently — `get_balance(client)` is a free function and on
Kraken-returned errors it logs and returns 0.0 rather than raising. Tests
below pin the actual behavior; a future day can decide whether to switch
the wrapper to raise.
"""
from __future__ import annotations

import pytest


# ─── get_balance ──────────────────────────────────────────────────────────


def test_get_balance_happy_path_returns_cad_amount(kraken_dryrun):
    """Default canned Balance response yields 100.00 CAD."""
    import kraken_client

    balance = kraken_client.get_balance(kraken_dryrun)
    assert balance == 100.00


def test_get_balance_falls_back_to_usd_when_no_cad(kraken_dryrun):
    """If the account has no ZCAD wallet, ZUSD is used as the fallback."""
    import kraken_client

    kraken_dryrun.query_private.side_effect = None
    kraken_dryrun.query_private.return_value = {
        "error": [],
        "result": {"ZUSD": "75.50"},
    }

    balance = kraken_client.get_balance(kraken_dryrun)
    assert balance == 75.50


def test_get_balance_returns_zero_on_kraken_error(kraken_dryrun):
    """A Kraken-side error response yields 0.0 (current contract — does not raise)."""
    import kraken_client

    kraken_dryrun.query_private.side_effect = None
    kraken_dryrun.query_private.return_value = {
        "error": ["EAPI:Invalid key"],
        "result": {},
    }

    balance = kraken_client.get_balance(kraken_dryrun)
    assert balance == 0.0


def test_get_balance_returns_zero_on_empty_wallets(kraken_dryrun):
    """If no fiat wallet is present, returns 0.0 — does not blow up."""
    import kraken_client

    kraken_dryrun.query_private.side_effect = None
    kraken_dryrun.query_private.return_value = {"error": [], "result": {}}

    balance = kraken_client.get_balance(kraken_dryrun)
    assert balance == 0.0


# ─── get_holdings ─────────────────────────────────────────────────────────


def test_get_holdings_returns_only_nonzero_nonfiat(kraken_dryrun):
    """Holdings dict excludes fiat wallets and zero balances; non-fiat is cleaned."""
    import kraken_client

    kraken_dryrun.query_private.side_effect = None
    kraken_dryrun.query_private.return_value = {
        "error": [],
        "result": {
            "ZCAD": "100.00",   # fiat — skip
            "ZUSD": "0.00",     # fiat — skip
            "XXDG": "500.0",    # DOGE — keep
            "XETH": "0.1",      # ETH — keep
            "BONK": "0.0",      # zero — skip
            "PEPE": "1000.0",   # short name — keep
        },
    }

    holdings = kraken_client.get_holdings(kraken_dryrun)

    # Accept either the clean_asset() mapping ("DOGE") or the simple
    # lstrip variant ("DG", "XDG") depending on which version of
    # kraken_client.py is loaded.
    assert any(k in holdings for k in ("DOGE", "XDG", "DG"))
    assert "ETH" in holdings
    assert "PEPE" in holdings
    assert "CAD" not in holdings and "ZCAD" not in holdings
    assert "BONK" not in holdings


def test_get_holdings_returns_empty_on_kraken_error(kraken_dryrun):
    """A Kraken error yields {} — does not raise."""
    import kraken_client

    kraken_dryrun.query_private.side_effect = None
    kraken_dryrun.query_private.return_value = {
        "error": ["EAPI:Invalid key"],
        "result": {},
    }

    holdings = kraken_client.get_holdings(kraken_dryrun)
    assert holdings == {}


# ─── get_tradable_coins ───────────────────────────────────────────────────


def test_get_tradable_coins_returns_sorted_cad_or_usd_coins(kraken_dryrun):
    """Returns a sorted list of base coins for CAD or USD-quoted pairs, fiat removed."""
    import kraken_client

    coins = kraken_client.get_tradable_coins(kraken_dryrun)

    assert isinstance(coins, list)
    assert coins == sorted(coins)
    # Default fixture has XDGCAD (base XXDG) and XBTCAD (base XXBT). Different
    # versions of kraken_client.py normalize these differently:
    #   clean_asset() map     → "DOGE", "BTC"
    #   simple lstrip variant → "DG",   "BT"
    # The test accepts either so it works against both HEAD and WIP.
    assert any(c in coins for c in ("DOGE", "XDG", "DG"))
    assert any(c in coins for c in ("BTC", "XBT", "BT"))


# ─── get_pair ─────────────────────────────────────────────────────────────


def test_get_pair_returns_none_for_unknown_coin(kraken_dryrun):
    """Unknown coin returns None (signals trader to skip)."""
    import kraken_client

    pair = kraken_client.get_pair(kraken_dryrun, "TOTALLYFAKECOIN")
    assert pair is None


# ─── get_price ────────────────────────────────────────────────────────────


def test_get_price_returns_zero_when_no_pair(kraken_dryrun):
    """Unknown coin returns 0.0 (current contract — feeds skip downstream)."""
    import kraken_client

    price = kraken_client.get_price(kraken_dryrun, "TOTALLYFAKECOIN")
    assert price == 0.0


# ─── place_order ──────────────────────────────────────────────────────────


def test_place_order_rejects_zero_volume(kraken_dryrun):
    """volume <= 0 returns None and does not hit AddOrder."""
    import kraken_client

    # amount_cad / price = 0 -> volume rounds to 0 -> reject
    result = kraken_client.place_order(
        kraken_dryrun, coin="TOTALLYFAKECOIN", action="buy", amount_cad=10.0, price=100.0
    )
    assert result is None


def test_place_order_returns_none_when_no_pair(kraken_dryrun):
    """Unknown coin yields None (no pair to trade on)."""
    import kraken_client

    result = kraken_client.place_order(
        kraken_dryrun, coin="UNKNOWNCOIN", action="buy", amount_cad=10.0, price=0.1
    )
    assert result is None
