"""Day 19 contract: every Kraken API call honors a minimum 1-second interval.

Three behaviors pinned:
1. Back-to-back calls within `MIN_CALL_INTERVAL_SEC` invoke `time.sleep`
   with a positive delay that closes the gap to the minimum.
2. A call after the interval has fully elapsed does NOT sleep.
3. The first call ever (cold start) does not sleep.

Uses `mocker.patch` on `kraken_client.time.sleep` and
`kraken_client.time.monotonic` so the limiter logic runs against synthetic
clock values without pausing pytest.
"""
from __future__ import annotations

import pytest


@pytest.fixture
def kc_with_clock(mocker):
    """Import kraken_client with time.sleep and time.monotonic mocked.

    Resets the limiter's internal `_last_call_monotonic` to 0 so each test
    starts from a known cold-start state.
    """
    import kraken_client

    kraken_client._last_call_monotonic = 0.0

    mock_sleep = mocker.patch("kraken_client.time.sleep")
    mock_monotonic = mocker.patch("kraken_client.time.monotonic")

    return kraken_client, mock_sleep, mock_monotonic


# ─── Contract: rate limiter sleeps when interval not yet elapsed ──────────


def test_back_to_back_calls_sleep_to_enforce_min_interval(kc_with_clock):
    """Two `_rate_limit()` calls within 1 second sleep for the remaining gap."""
    kc, mock_sleep, mock_monotonic = kc_with_clock

    # First call: monotonic returns 100.0 (twice — once for `now`, once for the post-update).
    # Second call: monotonic returns 100.3 (twice).
    mock_monotonic.side_effect = [100.0, 100.0, 100.3, 100.3]

    kc._rate_limit()  # cold start — no sleep expected
    kc._rate_limit()  # 0.3s after last call — must sleep ~0.7s

    # Cold start: at most one sleep call from the second invocation.
    assert mock_sleep.call_count == 1
    delay = mock_sleep.call_args[0][0]
    # Sleep close to (1.0 - 0.3) = 0.7s; allow tiny float epsilon
    assert 0.6 < delay < 0.71


def test_rate_limit_min_interval_constant_is_one_second():
    """The configured minimum interval matches the done-when spec."""
    import kraken_client

    assert kraken_client.MIN_CALL_INTERVAL_SEC == 1.0


# ─── Contract: no sleep when interval already elapsed ─────────────────────


def test_rate_limit_skips_sleep_when_interval_elapsed(kc_with_clock):
    """A call after >=1 second since the previous call does not sleep."""
    kc, mock_sleep, mock_monotonic = kc_with_clock

    # First call at t=100, second call at t=102 (2 seconds later).
    mock_monotonic.side_effect = [100.0, 100.0, 102.0, 102.0]

    kc._rate_limit()  # cold start
    kc._rate_limit()  # 2.0s later — no sleep

    assert mock_sleep.call_count == 0


# ─── Contract: cold start never sleeps ────────────────────────────────────


def test_first_call_does_not_sleep(kc_with_clock):
    """A cold-start `_rate_limit()` call doesn't pause — there's no history yet."""
    kc, mock_sleep, mock_monotonic = kc_with_clock

    mock_monotonic.side_effect = [50.0, 50.0]
    kc._rate_limit()

    assert mock_sleep.call_count == 0


# ─── Contract: limiter is called on every public Kraken function ──────────


def test_call_private_invokes_rate_limiter(mocker):
    """_call_private calls _rate_limit() before hitting the network."""
    import kraken_client

    mock_rl = mocker.patch.object(kraken_client, "_rate_limit")
    mocker.patch.object(kraken_client._call_private.retry, "wait", __import__("tenacity").wait_none())

    client = mocker.MagicMock()
    client.query_private.return_value = {"error": [], "result": {"ZCAD": "100.00"}}

    kraken_client._call_private(client, "Balance")

    assert mock_rl.call_count == 1


def test_call_public_invokes_rate_limiter(mocker):
    """_call_public calls _rate_limit() before hitting the network."""
    import kraken_client

    mock_rl = mocker.patch.object(kraken_client, "_rate_limit")
    mocker.patch.object(kraken_client._call_public.retry, "wait", __import__("tenacity").wait_none())

    client = mocker.MagicMock()
    client.query_public.return_value = {"error": [], "result": {"XBTZUSD": {}}}

    kraken_client._call_public(client, "AssetPairs")

    assert mock_rl.call_count == 1
