"""Unit tests for `market_matcher.analyze_news_for_trades`.

The function sends headlines and the tradable-coin list to Claude and parses
a JSON-array response. These tests mock the Anthropic call so they never
touch the network, and exercise four behaviors:

1. A high-confidence buy/sell on a known coin makes it through the filter.
2. A signal below `MIN_CONFIDENCE` is filtered out.
3. A signal for a coin Claude invented (not in available_coins) does not
   crash the function — it passes through (current behavior, future Day-N
   item could tighten this).
4. Malformed JSON from Claude is caught and returns an empty list.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────


def _fake_claude_response(text: str) -> MagicMock:
    """Build a MagicMock shaped like `anthropic.types.Message`.

    The real method returns an object whose `.content` is a list of blocks
    each carrying a `.text` attribute. `market_matcher` reads `content[0].text`.
    """
    block = MagicMock()
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


@pytest.fixture
def patched_market_matcher(mocker):
    """Import `market_matcher` with its Anthropic client.messages.create patched.

    Returns the module so tests can call its functions and assert against
    its constants. The patch is scoped per-test via pytest-mock.
    """
    import market_matcher

    mocker.patch.object(market_matcher.client, "messages", MagicMock())
    return market_matcher


# ─── Tests ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("coin", ["DOGE", "SHIB", "PEPE"])
def test_known_coin_high_confidence_signal_passes(patched_market_matcher, coin):
    """A 0.95-confidence buy on a known coin survives the MIN_CONFIDENCE filter."""
    mm = patched_market_matcher
    fake_json = (
        f'[{{"coin": "{coin}", "action": "buy", "confidence": 0.95, '
        f'"reasoning": "Elon tweeted about {coin}"}}]'
    )
    mm.client.messages.create.return_value = _fake_claude_response(fake_json)

    signals = mm.analyze_news_for_trades(
        headlines=f"1. Elon Musk tweets about {coin}",
        available_coins=["DOGE", "SHIB", "PEPE", "BTC"],
    )

    assert len(signals) == 1
    assert signals[0]["coin"] == coin
    assert signals[0]["action"] == "buy"
    assert signals[0]["confidence"] >= mm.MIN_CONFIDENCE


def test_low_confidence_signal_filtered_out(patched_market_matcher):
    """A 0.30-confidence signal is dropped by the MIN_CONFIDENCE post-filter."""
    mm = patched_market_matcher
    fake_json = (
        '[{"coin": "DOGE", "action": "buy", "confidence": 0.30, '
        '"reasoning": "weak rumor"}]'
    )
    mm.client.messages.create.return_value = _fake_claude_response(fake_json)

    signals = mm.analyze_news_for_trades(
        headlines="1. some weak rumor about DOGE",
        available_coins=["DOGE", "SHIB"],
    )

    assert signals == []


def test_unknown_coin_handled_gracefully(patched_market_matcher):
    """Claude inventing a coin not in available_coins does NOT raise.

    Current behavior: market_matcher does not enforce membership in
    available_coins; the signal passes through. The contract this test
    pins is "no exception" — the trader layer is responsible for skipping
    coins it cannot price (`get_price` returns 0.0 for unknown pairs).
    """
    mm = patched_market_matcher
    fake_json = (
        '[{"coin": "FAKECOIN", "action": "buy", "confidence": 0.95, '
        '"reasoning": "hallucinated"}]'
    )
    mm.client.messages.create.return_value = _fake_claude_response(fake_json)

    signals = mm.analyze_news_for_trades(
        headlines="1. mention of nothing",
        available_coins=["DOGE", "SHIB"],
    )

    assert isinstance(signals, list)
    assert len(signals) == 1
    assert signals[0]["coin"] == "FAKECOIN"


def test_malformed_json_returns_empty_list(patched_market_matcher):
    """Non-JSON response from Claude is caught and returns []."""
    mm = patched_market_matcher
    mm.client.messages.create.return_value = _fake_claude_response(
        "this is not valid json at all, just prose"
    )

    signals = mm.analyze_news_for_trades(
        headlines="1. nothing actionable here",
        available_coins=["DOGE"],
    )

    assert signals == []


def test_fenced_code_block_stripped(patched_market_matcher):
    """Claude wrapping JSON in ```json ... ``` fences is unwrapped before parse."""
    mm = patched_market_matcher
    fenced = (
        "```json\n"
        '[{"coin": "DOGE", "action": "buy", "confidence": 0.95, "reasoning": "x"}]\n'
        "```"
    )
    mm.client.messages.create.return_value = _fake_claude_response(fenced)

    signals = mm.analyze_news_for_trades(
        headlines="1. DOGE news",
        available_coins=["DOGE"],
    )

    assert len(signals) == 1
    assert signals[0]["coin"] == "DOGE"


def test_anthropic_exception_returns_empty_list(patched_market_matcher):
    """If the Anthropic SDK raises, the function returns [] rather than crashing."""
    mm = patched_market_matcher
    mm.client.messages.create.side_effect = RuntimeError("simulated network failure")

    signals = mm.analyze_news_for_trades(
        headlines="1. anything",
        available_coins=["DOGE"],
    )

    assert signals == []
