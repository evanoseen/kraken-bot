"""Shared pytest fixtures for the kraken-bot test suite.

The `kraken_dryrun` fixture returns a `MagicMock` shaped like a `krakenex.API`
instance with `query_private` and `query_public` methods preloaded with sane
no-op responses. Individual tests can override any endpoint by reassigning
`client.query_private.side_effect` or by stacking `mocker.patch` calls on top.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


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
