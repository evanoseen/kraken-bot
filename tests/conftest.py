"""Shared pytest fixtures for the kraken-bot test suite.

The `kraken_dryrun` fixture returns a `MagicMock` shaped like a `krakenex.API`
instance with `query_private` and `query_public` methods preloaded with sane
no-op responses. Individual tests can override any endpoint by reassigning
`client.query_private.side_effect` or by stacking `mocker.patch` calls on top.

`reset_kraken_rate_limiter` (autouse) keeps the Day 19 rate limiter from
slowing tests that don't explicitly verify it. Each test starts with the
limiter cold and `time.sleep` replaced with a no-op. Tests that want to
observe the limiter's behavior (`tests/test_kraken_rate_limit.py`) install
their own clock mocks on top.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def reset_kraken_rate_limiter(mocker):
    """Cold-start the limiter and neutralize `time.sleep` for every test."""
    try:
        import kraken_client
    except Exception:
        return

    kraken_client._last_call_monotonic = 0.0
    mocker.patch("kraken_client.time.sleep")


@pytest.fixture
def fast_retry(mocker):
    """Patch retry wait + rate-limiter sleep to zero so retry-exhaustion
    tests stay fast (Day 18 added tenacity exponential backoff; Day 19
    added a rate-limiter sleep). Both are neutralized here so the retry
    logic still runs but the test finishes in milliseconds instead of
    seconds. Moved here from tests/test_kraken_retry.py (Day 80) so
    tests/test_kraken_client.py can reuse it too.
    """
    import kraken_client
    from tenacity import wait_none

    mocker.patch.object(kraken_client._call_private.retry, "wait", wait_none())
    mocker.patch.object(kraken_client._call_public.retry, "wait", wait_none())
    mocker.patch("kraken_client.time.sleep")
    return kraken_client


@pytest.fixture(autouse=True)
def reset_headline_cache():
    """Clear the Day 47 seen-headline set so tests never see stale state
    left over from a different test module's mocked headlines."""
    try:
        import headline_cache
    except Exception:
        return

    headline_cache.reset()
    yield
    headline_cache.reset()


# ─── Canned Kraken responses ──────────────────────────────────────────────
# Shape mirrors the real Kraken REST API: {"error": [...], "result": {...}}.

_BALANCE_RESPONSE = {
    "error": [],
    "result": {"ZCAD": "100.00"},
}

_OPEN_ORDERS_RESPONSE = {
    "error": [],
    "result": {"open": {}},
}

_ADD_ORDER_RESPONSE = {
    "error": [],
    "result": {"descr": {"order": "buy 1.0 XDGCAD @ market"}, "txid": ["DRYRUN-TXID-0"]},
}

_CANCEL_ORDER_RESPONSE = {
    "error": [],
    "result": {"count": 1},
}

_ASSET_PAIRS_RESPONSE = {
    "error": [],
    "result": {
        "XDGCAD": {"base": "XXDG", "quote": "ZCAD"},
        "XBTCAD": {"base": "XXBT", "quote": "ZCAD"},
    },
}

_TICKER_RESPONSE = {
    "error": [],
    "result": {
        "XDGCAD": {
            "a": ["0.10000000", "1", "1.000"],   # ask
            "b": ["0.09500000", "1", "1.000"],   # bid
            "c": ["0.09800000", "1.0"],          # last close
            "v": ["1000.0", "10000.0"],          # volume today / 24h
            "p": ["0.09700000", "0.09600000"],   # vwap
            "t": [50, 500],                       # trade count today / 24h
            "l": ["0.09000000", "0.08500000"],   # low today / 24h
            "h": ["0.11000000", "0.11500000"],   # high today / 24h
            "o": "0.09500000",                    # opening price
        }
    },
}


def _default_private(endpoint: str, payload: dict | None = None) -> dict:
    """Return a canned response for a private-API call. Override in tests."""
    payload = payload or {}
    if endpoint == "Balance":
        return _BALANCE_RESPONSE
    if endpoint == "OpenOrders":
        return _OPEN_ORDERS_RESPONSE
    if endpoint == "AddOrder":
        return _ADD_ORDER_RESPONSE
    if endpoint == "CancelOrder":
        return _CANCEL_ORDER_RESPONSE
    return {"error": [f"EGeneral:Unknown private endpoint: {endpoint}"], "result": {}}


def _default_public(endpoint: str, payload: dict | None = None) -> dict:
    """Return a canned response for a public-API call. Override in tests."""
    payload = payload or {}
    if endpoint == "AssetPairs":
        return _ASSET_PAIRS_RESPONSE
    if endpoint == "Ticker":
        return _TICKER_RESPONSE
    return {"error": [f"EGeneral:Unknown public endpoint: {endpoint}"], "result": {}}


@pytest.fixture
def kraken_dryrun() -> MagicMock:
    """Return a MagicMock shaped like a krakenex.API client.

    The mock places no real network calls. `query_private` and `query_public`
    return canned responses keyed on the endpoint name. Tests can override
    behavior per-call with `side_effect` or replace the return value entirely
    via `client.query_private.return_value = {...}`.
    """
    client = MagicMock(name="kraken_dryrun_client")
    client.key = "DRYRUN_KEY"
    client.secret = "DRYRUN_SECRET"
    client.query_private = MagicMock(side_effect=_default_private)
    client.query_public = MagicMock(side_effect=_default_public)
    return client
