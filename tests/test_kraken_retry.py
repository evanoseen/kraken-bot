"""Day 18 contract: every Kraken API call retries on transient errors.

Pins three behaviors:
1. Public `kraken_client` functions that hit the network go through one
   of the two retry-decorated helpers (`_call_private` or `_call_public`).
2. A simulated 429 (`EAPI:Rate limit`) fires the retry — the underlying
   client method is called multiple times, and a final success after two
   transient failures returns the right value.
3. A non-transient error (`EAPI:Invalid key`) does NOT trigger retry —
   one call, immediate return.

To keep the suite fast, `_retry_kraken.wait` is monkeypatched to
`wait_none()` so we don't pay seconds of exponential backoff per test.
"""
from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from tenacity import wait_none


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def fast_retry(mocker):
    """Patch retry wait + rate-limiter sleep to zero so tests stay fast.

    Day 18 added tenacity exponential backoff between retries; Day 19 added
    a `time.sleep` rate limiter inside _call_private/_call_public. Both are
    neutralized here so retry/rate-limiter logic still runs but the test
    finishes in milliseconds instead of seconds.
    """
    import kraken_client

    mocker.patch.object(kraken_client._call_private.retry, "wait", wait_none())
    mocker.patch.object(kraken_client._call_public.retry, "wait", wait_none())
    mocker.patch("kraken_client.time.sleep")
    return kraken_client


# ─── Contract: every network-hitting function uses a retry helper ─────────


def test_every_network_function_routes_through_a_retry_helper():
    """AST audit: each public Kraken function calls either _call_private or _call_public.

    Catches the regression where someone adds a new function that calls
    `client.query_private(...)` directly and bypasses the retry layer.
    """
    src = (REPO_ROOT / "kraken_client.py").read_text()
    tree = ast.parse(src)

    network_funcs = {
        "get_balance", "get_holdings", "get_tradable_coins",
        "get_pair", "get_price", "place_order",
    }
    helpers = {"_call_private", "_call_public"}

    findings: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in network_funcs:
            continue

        used = set()
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Name):
                used.add(sub.func.id)
            if isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
                # catches the regression: client.query_private(...)
                if sub.func.attr in ("query_private", "query_public"):
                    findings.append(
                        f"{node.name} calls client.{sub.func.attr} directly — "
                        f"must route through {sorted(helpers)}"
                    )

        if not (used & helpers):
            findings.append(f"{node.name} uses none of {sorted(helpers)}")

    assert not findings, "\n  " + "\n  ".join(findings)


# ─── Behavior: rate-limit retries, final success ──────────────────────────


def test_rate_limit_429_triggers_retry_then_succeeds(fast_retry, kraken_dryrun):
    """A simulated EAPI:Rate limit on the first two calls retries until success."""
    kc = fast_retry

    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    success = {"error": [], "result": {"ZCAD": "200.00"}}

    # Two transient failures, then a real balance
    kraken_dryrun.query_private.side_effect = [rate_limited, rate_limited, success]

    balance = kc.get_balance(kraken_dryrun)

    assert balance == 200.00, "final balance should reflect the third (successful) call"
    assert kraken_dryrun.query_private.call_count == 3, (
        "expected 3 calls: 2 retried + 1 success, got "
        f"{kraken_dryrun.query_private.call_count}"
    )


def test_rate_limit_429_exhausts_retries_then_returns_default(fast_retry, kraken_dryrun):
    """Three rate-limit responses exhaust the `stop_after_attempt(3)` budget."""
    kc = fast_retry

    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    kraken_dryrun.query_private.side_effect = [rate_limited] * 5  # more than enough

    balance = kc.get_balance(kraken_dryrun)

    # Public function swallows the final KrakenTransientError and returns 0.0
    assert balance == 0.0
    # stop_after_attempt(3) means max 3 invocations
    assert kraken_dryrun.query_private.call_count == 3


def test_service_unavailable_is_also_transient(fast_retry, kraken_dryrun):
    """EService:Unavailable is in the transient set — retries fire."""
    kc = fast_retry

    unavailable = {"error": ["EService:Unavailable"], "result": {}}
    success = {"error": [], "result": {"ZCAD": "50.00"}}

    kraken_dryrun.query_private.side_effect = [unavailable, success]
    balance = kc.get_balance(kraken_dryrun)

    assert balance == 50.00
    assert kraken_dryrun.query_private.call_count == 2


# ─── Behavior: non-transient errors do NOT trigger retry ──────────────────


def test_invalid_key_does_not_retry(fast_retry, kraken_dryrun):
    """A non-transient error returns immediately — no retries."""
    kc = fast_retry

    invalid = {"error": ["EAPI:Invalid key"], "result": {}}
    kraken_dryrun.query_private.side_effect = [invalid]  # exactly one allowed

    balance = kc.get_balance(kraken_dryrun)

    assert balance == 0.0
    assert kraken_dryrun.query_private.call_count == 1, (
        "non-transient errors must not trigger retry"
    )


def test_public_endpoint_retry_on_rate_limit(fast_retry, kraken_dryrun):
    """Public Ticker also retries on rate limit, via `_call_public`."""
    kc = fast_retry

    rate_limited = {"error": ["EAPI:Rate limit exceeded"], "result": {}}
    # Use a base name that resolves to DOGE through both the HEAD lstrip
    # variant and the WIP clean_asset map.
    default_pairs = {
        "error": [],
        "result": {
            "DOGECAD": {"base": "DOGE", "quote": "ZCAD"},
        },
    }
    success_ticker = {
        "error": [],
        "result": {
            "XDGCAD": {
                "a": ["0.42000000", "1", "1.000"],
                "b": ["0.41000000", "1", "1.000"],
                "c": ["0.41500000", "1.0"],
                "v": ["1.0", "1.0"],
                "p": ["0.41500000", "0.41500000"],
                "t": [1, 1],
                "l": ["0.40000000", "0.40000000"],
                "h": ["0.45000000", "0.45000000"],
                "o": "0.41000000",
            }
        },
    }

    def public_side_effect(endpoint, payload=None):
        if endpoint == "AssetPairs":
            return default_pairs
        if endpoint == "Ticker":
            # rate limit twice, then succeed
            if public_side_effect.ticker_calls < 2:
                public_side_effect.ticker_calls += 1
                return rate_limited
            return success_ticker
        return {"error": [], "result": {}}

    public_side_effect.ticker_calls = 0  # type: ignore[attr-defined]
    kraken_dryrun.query_public.side_effect = public_side_effect

    price = kc.get_price(kraken_dryrun, "DOGE")
    assert price == 0.42
