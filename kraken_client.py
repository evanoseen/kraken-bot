"""Thin wrapper around the krakenex REST client.

Day 18 added `tenacity` retries with exponential backoff on every method
that makes a network call. The two private helpers `_call_private` and
`_call_public` are the only functions that actually touch the network;
they are decorated with `@retry` so the public functions (get_balance,
get_holdings, get_tradable_coins, get_pair, get_price, place_order) get
retry behavior for free.

Day 22 added latency logging in the same two helpers: each times only the
network call (excluding the rate-limit gate) and emits
`kraken.<private|public>/<endpoint> took N.NNs` at INFO. Because every method
routes through these helpers, every Kraken call logs its latency for free —
slow responses surface in journalctl before they become an outage.

What counts as "transient" and is retried:
- HTTP-layer exceptions raised by krakenex (timeouts, 5xx responses)
- Kraken-level rate-limit responses: `EAPI:Rate limit exceeded`
- Kraken-level service-unavailable: `EService:Unavailable`, `EService:Busy`

What is NOT retried:
- Auth errors (`EAPI:Invalid key`) — these will not fix themselves
- Validation errors (`EOrder:Invalid arguments`) — same
- Successful responses (no `error` field)
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import krakenex
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from config import cfg

logger = logging.getLogger(__name__)


# ─── Rate limiter ─────────────────────────────────────────────────────────
#
# Kraken throttles per IP. The public-tier limit is ~1 call/second for
# unauthenticated traffic and tighter on the authenticated tier. A
# minimum-interval gate before every API call keeps us inside the budget
# even when retries fire in quick succession.

MIN_CALL_INTERVAL_SEC: float = 1.0

_last_call_monotonic: float = 0.0


def _rate_limit() -> None:
    """Block until at least `MIN_CALL_INTERVAL_SEC` has passed since the last call.

    Uses `time.monotonic()` so DST and NTP adjustments cannot wedge the
    limiter. Updates the gate immediately after sleeping so concurrent
    retries don't pile into the same window.
    """
    global _last_call_monotonic
    now = time.monotonic()
    elapsed = now - _last_call_monotonic
    if 0.0 < elapsed < MIN_CALL_INTERVAL_SEC:
        time.sleep(MIN_CALL_INTERVAL_SEC - elapsed)
    _last_call_monotonic = time.monotonic()


class KrakenTransientError(Exception):
    """Raised when a Kraken response indicates a retryable transient failure.

    Includes Kraken-side rate limits (HTTP 429 family — `EAPI:Rate limit`)
    and service-unavailable responses (`EService:Unavailable`, `EService:Busy`).
    The `tenacity` `@retry` decorator catches this type and re-invokes the
    call up to `stop_after_attempt(3)` with exponential backoff.
    """


# A Kraken error string is "transient" if it contains any of these substrings.
_TRANSIENT_PREFIXES: tuple[str, ...] = (
    "EAPI:Rate limit",
    "EService:Unavailable",
    "EService:Busy",
)


def _is_transient(errors: list[str]) -> bool:
    """Return True if any error string in `errors` is a transient Kraken failure."""
    return any(
        any(prefix in err for prefix in _TRANSIENT_PREFIXES)
        for err in errors
    )


_retry_kraken = retry(
    retry=retry_if_exception_type((KrakenTransientError, ConnectionError, TimeoutError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(min=1, max=10),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)


@_retry_kraken
def _call_private(client: krakenex.API, endpoint: str, payload: Optional[dict] = None) -> dict:
    """Invoke a private Kraken REST endpoint with rate limit + retry on transient errors.

    Returns the full response dict (including any non-transient `error` list).
    Raises `KrakenTransientError` on transient errors so `tenacity` retries.
    """
    _rate_limit()
    t0 = time.monotonic()
    resp = client.query_private(endpoint, payload) if payload else client.query_private(endpoint)
    logger.info("kraken.private/%s took %.2fs", endpoint, time.monotonic() - t0)
    errors = resp.get("error") or []
    if _is_transient(errors):
        raise KrakenTransientError(f"transient Kraken error on private/{endpoint}: {errors}")
    return resp


@_retry_kraken
def _call_public(client: krakenex.API, endpoint: str, payload: Optional[dict] = None) -> dict:
    """Invoke a public Kraken REST endpoint with rate limit + retry on transient errors."""
    _rate_limit()
    t0 = time.monotonic()
    resp = client.query_public(endpoint, payload) if payload else client.query_public(endpoint)
    logger.info("kraken.public/%s took %.2fs", endpoint, time.monotonic() - t0)
    errors = resp.get("error") or []
    if _is_transient(errors):
        raise KrakenTransientError(f"transient Kraken error on public/{endpoint}: {errors}")
    return resp


def get_client() -> krakenex.API:
    """Build and return an authenticated krakenex REST client.

    Side effects: reads `KRAKEN_API_KEY` and `KRAKEN_PRIVATE_KEY` from config
    and attaches them to the client. No network call.
    """
    k = krakenex.API()
    k.key = cfg.kraken_api_key
    k.secret = cfg.kraken_private_key
    return k


def get_balance(client: krakenex.API) -> float:
    """Return the account's fiat balance in CAD, falling back to USD if no CAD wallet.

    Args: `client` is a krakenex API instance from `get_client()`.
    Returns: float CAD (or USD) balance, or 0.0 on API error.
    Side effects: one private REST call to Kraken's `Balance` endpoint; logs errors.
    Network calls are wrapped in `@retry` via `_call_private`.
    """
    try:
        resp = _call_private(client, "Balance")
    except KrakenTransientError as e:
        logger.error(f"Balance: retries exhausted: {e}")
        return 0.0

    if resp.get("error"):
        logger.error(f"Balance error: {resp['error']}")
        return 0.0
    balances = resp.get("result", {})
    return float(balances.get("ZCAD", balances.get("ZUSD", balances.get("CAD", balances.get("USD", 0)))))


def get_holdings(client: krakenex.API) -> dict[str, float]:
    """Return dict of {symbol: amount} for coins currently held."""
    try:
        resp = _call_private(client, "Balance")
    except KrakenTransientError as e:
        logger.error(f"Holdings: retries exhausted: {e}")
        return {}

    if resp.get("error"):
        return {}
    balances = resp.get("result", {})
    holdings: dict[str, float] = {}
    skip = {"ZCAD", "ZUSD", "ZEUR", "CAD", "USD", "EUR"}
    for key, val in balances.items():
        amount = float(val)
        if amount > 0 and key not in skip:
            clean = key.lstrip("X").lstrip("Z") if len(key) > 3 else key
            holdings[clean] = amount
    return holdings


def get_tradable_coins(client: krakenex.API) -> list[str]:
    """Fetch all coins tradable in CAD or USD on Kraken."""
    try:
        resp = _call_public(client, "AssetPairs")
    except KrakenTransientError as e:
        logger.error(f"AssetPairs: retries exhausted: {e}")
        return []

    if resp.get("error"):
        logger.error(f"AssetPairs error: {resp['error']}")
        return []

    coins = set()
    for pair_name, pair_info in resp.get("result", {}).items():
        quote = pair_info.get("quote", "")
        base = pair_info.get("base", "")
        if quote in ("ZCAD", "ZUSD", "CAD", "USD"):
            clean = base.lstrip("X").lstrip("Z") if len(base) > 3 else base
            if clean not in ("CAD", "USD", "EUR", "GBP"):
                coins.add(clean)

    return sorted(list(coins))


def get_pair(client: krakenex.API, coin: str) -> Optional[str]:
    """Find the best trading pair for a coin (prefer CAD, fallback USD)."""
    try:
        resp = _call_public(client, "AssetPairs")
    except KrakenTransientError as e:
        logger.error(f"AssetPairs (get_pair): retries exhausted: {e}")
        return None

    if resp.get("error"):
        return None

    cad_pair = None
    usd_pair = None

    for pair_name, pair_info in resp.get("result", {}).items():
        base = pair_info.get("base", "").lstrip("X").lstrip("Z")
        quote = pair_info.get("quote", "")
        if base.upper() == coin.upper() or base.upper() == f"X{coin.upper()}":
            if quote in ("ZCAD", "CAD"):
                cad_pair = pair_name
            elif quote in ("ZUSD", "USD") and not cad_pair:
                usd_pair = pair_name

    return cad_pair or usd_pair


def get_price(client: krakenex.API, coin: str) -> float:
    """Get current ask price for a coin."""
    pair = get_pair(client, coin)
    if not pair:
        return 0.0
    try:
        resp = _call_public(client, "Ticker", {"pair": pair})
    except KrakenTransientError as e:
        logger.error(f"Ticker {pair}: retries exhausted: {e}")
        return 0.0
    if resp.get("error"):
        return 0.0
    result = resp.get("result", {})
    for key, val in result.items():
        return float(val["a"][0])
    return 0.0


def place_order(
    client: krakenex.API,
    coin: str,
    action: str,
    amount_cad: float,
    price: float,
) -> Optional[dict]:
    """Place a market order. action: 'buy' or 'sell'"""
    pair = get_pair(client, coin)
    if not pair:
        logger.error(f"No pair found for {coin}")
        return None

    volume = round(amount_cad / price, 6)
    if volume <= 0:
        logger.warning(f"Volume too small for {coin}")
        return None

    try:
        resp = _call_private(client, "AddOrder", {
            "pair": pair,
            "type": action,
            "ordertype": "market",
            "volume": str(volume),
        })
    except KrakenTransientError as e:
        logger.error(f"AddOrder {coin}: retries exhausted: {e}")
        return None

    if resp.get("error"):
        logger.error(f"Order error for {coin}: {resp['error']}")
        return None

    logger.info(f"Order placed: {action} {volume} {coin} (~${amount_cad:.2f}) | {resp['result']}")
    return resp["result"]
