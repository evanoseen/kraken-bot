"""Day 22 contract: every Kraken API call logs its network latency.

Both network helpers (`_call_private`, `_call_public`) time only the network
call — not the rate-limit gate — and emit `kraken.<kind>/<endpoint> took N.NNs`
at INFO on every call. Verified for both helpers, with and without a payload.

We assert the log-line *shape* rather than an exact duration: the mocked client
returns instantly, so real `time.monotonic()` yields a tiny but well-formed
elapsed. (Patching `kraken_client.time.monotonic` is avoided on purpose — it
aliases the global `time.monotonic`, which tenacity's retry loop also calls.)
The retry `wait` is set to `wait_none()` so a transient path wouldn't pause pytest.
"""
from __future__ import annotations

import logging
import re

import pytest
from tenacity import wait_none

LATENCY_RE = re.compile(r"kraken\.(private|public)/(\w+) took \d+\.\d{2}s")


@pytest.fixture
def kc(mocker):
    """kraken_client with retry backoff neutralized and the limiter stubbed out."""
    import kraken_client

    mocker.patch.object(kraken_client, "_rate_limit")
    mocker.patch.object(kraken_client._call_private.retry, "wait", wait_none())
    mocker.patch.object(kraken_client._call_public.retry, "wait", wait_none())
    return kraken_client


def test_private_call_logs_latency(kc, mocker, caplog):
    """_call_private logs `kraken.private/Balance took N.NNs`."""
    client = mocker.MagicMock()
    client.query_private.return_value = {"error": [], "result": {"ZCAD": "100.00"}}

    with caplog.at_level(logging.INFO, logger="kraken_client"):
        kc._call_private(client, "Balance")

    assert "kraken.private/Balance took " in caplog.text
    assert LATENCY_RE.search(caplog.text)


def test_public_call_logs_latency(kc, mocker, caplog):
    """_call_public logs `kraken.public/AssetPairs took N.NNs`."""
    client = mocker.MagicMock()
    client.query_public.return_value = {"error": [], "result": {"XBTZUSD": {}}}

    with caplog.at_level(logging.INFO, logger="kraken_client"):
        kc._call_public(client, "AssetPairs")

    assert "kraken.public/AssetPairs took " in caplog.text
    assert LATENCY_RE.search(caplog.text)


def test_latency_logged_with_payload(kc, mocker, caplog):
    """The payload branch of the call is timed and logged too."""
    client = mocker.MagicMock()
    client.query_public.return_value = {"error": [], "result": {}}

    with caplog.at_level(logging.INFO, logger="kraken_client"):
        kc._call_public(client, "Ticker", {"pair": "XBTCAD"})

    assert "kraken.public/Ticker took " in caplog.text
    client.query_public.assert_called_once_with("Ticker", {"pair": "XBTCAD"})


def test_latency_logged_on_every_call(kc, mocker, caplog):
    """Two calls produce two latency log lines — logged on each call, not once."""
    client = mocker.MagicMock()
    client.query_private.return_value = {"error": [], "result": {}}

    with caplog.at_level(logging.INFO, logger="kraken_client"):
        kc._call_private(client, "OpenOrders")
        kc._call_private(client, "Balance")

    lines = [m.group(0) for m in LATENCY_RE.finditer(caplog.text)]
    assert len(lines) == 2
    assert any("OpenOrders" in line for line in lines)
    assert any("Balance" in line for line in lines)
