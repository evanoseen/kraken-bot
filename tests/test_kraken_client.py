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


# ─── get_client ───────────────────────────────────────────────────────────


def test_get_client_attaches_key_and_secret_from_config(mocker):
    """Day 80: get_client() had zero direct coverage — every other test
    goes straight to the kraken_dryrun mock instead. cfg is a frozen
    dataclass, so the module-level reference is replaced wholesale rather
    than mutating an attribute on it."""
    import kraken_client

    mocker.patch(
        "kraken_client.cfg",
        mocker.Mock(kraken_api_key="test-api-key", kraken_private_key="test-private-key"),
    )

    client = kraken_client.get_client()

    assert client.key == "test-api-key"
    assert client.secret == "test-private-key"


def test_get_client_makes_no_network_call(mocker):
    import kraken_client

    call_private = mocker.patch.object(kraken_client, "_call_private")
    call_public = mocker.patch.object(kraken_client, "_call_public")

    kraken_client.get_client()

    call_private.assert_not_called()
    call_public.assert_not_called()


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


def test_get_holdings_returns_empty_when_retries_exhausted(fast_retry, kraken_dryrun):
    kc = fast_retry
    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_private.side_effect = [rate_limited] * 5
    assert kc.get_holdings(kraken_dryrun) == {}


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


def test_get_tradable_coins_returns_empty_on_kraken_error(kraken_dryrun):
    kraken_dryrun.query_public.side_effect = None
    kraken_dryrun.query_public.return_value = {"error": ["EGeneral:Unknown"], "result": {}}
    import kraken_client
    assert kraken_client.get_tradable_coins(kraken_dryrun) == []


def test_get_tradable_coins_returns_empty_when_retries_exhausted(fast_retry, kraken_dryrun):
    kc = fast_retry
    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_public.side_effect = [rate_limited] * 5
    assert kc.get_tradable_coins(kraken_dryrun) == []


# ─── get_pair ─────────────────────────────────────────────────────────────


def test_get_pair_returns_none_for_unknown_coin(kraken_dryrun):
    """Unknown coin returns None (signals trader to skip)."""
    import kraken_client

    pair = kraken_client.get_pair(kraken_dryrun, "TOTALLYFAKECOIN")
    assert pair is None


def test_get_pair_returns_cad_pair_for_known_coin(kraken_dryrun):
    import kraken_client
    assert kraken_client.get_pair(kraken_dryrun, "DG") == "XDGCAD"


def test_get_pair_falls_back_to_usd_when_no_cad_pair(kraken_dryrun):
    kraken_dryrun.query_public.side_effect = None
    kraken_dryrun.query_public.return_value = {
        "error": [],
        "result": {"XDGUSD": {"base": "XXDG", "quote": "ZUSD"}},
    }
    import kraken_client
    assert kraken_client.get_pair(kraken_dryrun, "DG") == "XDGUSD"


def test_get_pair_prefers_cad_over_usd_when_both_exist(kraken_dryrun):
    kraken_dryrun.query_public.side_effect = None
    kraken_dryrun.query_public.return_value = {
        "error": [],
        "result": {
            "XDGUSD": {"base": "XXDG", "quote": "ZUSD"},
            "XDGCAD": {"base": "XXDG", "quote": "ZCAD"},
        },
    }
    import kraken_client
    assert kraken_client.get_pair(kraken_dryrun, "DG") == "XDGCAD"


def test_get_pair_returns_none_when_retries_exhausted(fast_retry, kraken_dryrun):
    kc = fast_retry
    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_public.side_effect = [rate_limited] * 5
    assert kc.get_pair(kraken_dryrun, "DG") is None


# ─── get_price ────────────────────────────────────────────────────────────


def test_get_price_returns_zero_when_no_pair(kraken_dryrun):
    """Unknown coin returns 0.0 (current contract — feeds skip downstream)."""
    import kraken_client

    price = kraken_client.get_price(kraken_dryrun, "TOTALLYFAKECOIN")
    assert price == 0.0


def test_get_price_returns_ask_price_for_known_coin(kraken_dryrun):
    """Happy path — default Ticker fixture's ask ("a") is 0.10000000."""
    import kraken_client
    assert kraken_client.get_price(kraken_dryrun, "DG") == 0.1


def test_get_price_returns_zero_on_kraken_error(kraken_dryrun):
    def query_public(endpoint, payload=None):
        if endpoint == "AssetPairs":
            return {"error": [], "result": {"XDGCAD": {"base": "XXDG", "quote": "ZCAD"}}}
        if endpoint == "Ticker":
            return {"error": ["EGeneral:Unknown"], "result": {}}
        return {"error": [], "result": {}}
    kraken_dryrun.query_public.side_effect = query_public
    import kraken_client
    assert kraken_client.get_price(kraken_dryrun, "DG") == 0.0


def test_get_price_returns_zero_when_ticker_result_is_empty(kraken_dryrun):
    def query_public(endpoint, payload=None):
        if endpoint == "AssetPairs":
            return {"error": [], "result": {"XDGCAD": {"base": "XXDG", "quote": "ZCAD"}}}
        if endpoint == "Ticker":
            return {"error": [], "result": {}}
        return {"error": [], "result": {}}
    kraken_dryrun.query_public.side_effect = query_public
    import kraken_client
    assert kraken_client.get_price(kraken_dryrun, "DG") == 0.0


def test_get_price_returns_zero_when_retries_exhausted(fast_retry, kraken_dryrun):
    kc = fast_retry

    def query_public(endpoint, payload=None):
        if endpoint == "AssetPairs":
            return {"error": [], "result": {"XDGCAD": {"base": "XXDG", "quote": "ZCAD"}}}
        return {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_public.side_effect = query_public
    assert kc.get_price(kraken_dryrun, "DG") == 0.0


# ─── place_order ──────────────────────────────────────────────────────────


def test_place_order_rejects_zero_volume(kraken_dryrun):
    """Unknown coin never reaches the volume calc — returns None via the
    'no pair' branch instead. Kept for the no-pair-with-a-would-be-zero-
    volume combination; see test_place_order_rejects_actually_zero_volume
    for the volume<=0 branch itself."""
    import kraken_client

    result = kraken_client.place_order(
        kraken_dryrun, coin="TOTALLYFAKECOIN", action="buy", amount_cad=10.0, price=100.0
    )
    assert result is None


def test_place_order_rejects_actually_zero_volume(kraken_dryrun, mocker):
    """A resolvable pair but amount_cad=0 exercises the volume<=0 guard
    itself, not the earlier no-pair branch."""
    import kraken_client

    logger_warning = mocker.spy(kraken_client.logger, "warning")
    result = kraken_client.place_order(
        kraken_dryrun, coin="DG", action="buy", amount_cad=0.0, price=0.1
    )
    assert result is None
    logger_warning.assert_called_once()
    assert "Volume too small" in logger_warning.call_args.args[0]


def test_place_order_returns_none_when_no_pair(kraken_dryrun):
    """Unknown coin yields None (no pair to trade on)."""
    import kraken_client

    result = kraken_client.place_order(
        kraken_dryrun, coin="UNKNOWNCOIN", action="buy", amount_cad=10.0, price=0.1
    )
    assert result is None


def test_place_order_happy_path_returns_result(kraken_dryrun):
    import kraken_client
    result = kraken_client.place_order(
        kraken_dryrun, coin="DG", action="buy", amount_cad=10.0, price=0.1
    )
    assert result is not None
    assert result["txid"] == ["DRYRUN-TXID-0"]


def test_place_order_sends_correct_pair_type_and_volume(kraken_dryrun):
    import kraken_client
    kraken_client.place_order(kraken_dryrun, coin="DG", action="sell", amount_cad=20.0, price=0.1)

    call_args = kraken_dryrun.query_private.call_args
    assert call_args.args[0] == "AddOrder"
    payload = call_args.args[1]
    assert payload["pair"] == "XDGCAD"
    assert payload["type"] == "sell"
    assert payload["ordertype"] == "market"
    assert payload["volume"] == str(round(20.0 / 0.1, 6))


def test_place_order_returns_none_on_kraken_error(kraken_dryrun):
    def query_private(endpoint, payload=None):
        if endpoint == "AddOrder":
            return {"error": ["EOrder:Insufficient funds"], "result": {}}
        return {"error": [], "result": {"ZCAD": "100.00"}}
    kraken_dryrun.query_private.side_effect = query_private
    import kraken_client
    result = kraken_client.place_order(kraken_dryrun, coin="DG", action="buy", amount_cad=10.0, price=0.1)
    assert result is None


def test_place_order_returns_none_when_retries_exhausted(fast_retry, kraken_dryrun):
    kc = fast_retry
    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_private.side_effect = [rate_limited] * 5
    result = kc.place_order(kraken_dryrun, coin="DG", action="buy", amount_cad=10.0, price=0.1)
    assert result is None
