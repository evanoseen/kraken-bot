"""Tests for Day 33 — signal deduplication."""
from signals import deduplicate


def _sig(coin, action="buy", confidence=0.80, reasoning="test"):
    return {"coin": coin, "action": action, "confidence": confidence, "reasoning": reasoning}


def test_no_dupes_unchanged():
    sigs = [_sig("DOGE"), _sig("SHIB")]
    result = deduplicate(sigs)
    assert len(result) == 2


def test_duplicate_coin_merged_to_one():
    sigs = [_sig("DOGE", confidence=0.80), _sig("DOGE", confidence=0.90)]
    result = deduplicate(sigs)
    assert len(result) == 1


def test_merged_takes_higher_confidence():
    sigs = [_sig("DOGE", confidence=0.75), _sig("DOGE", confidence=0.92)]
    result = deduplicate(sigs)
    assert result[0]["confidence"] == 0.92


def test_merged_concatenates_reasoning():
    sigs = [_sig("DOGE", reasoning="pump signal"), _sig("DOGE", reasoning="news signal")]
    result = deduplicate(sigs)
    assert "pump signal" in result[0]["reasoning"]
    assert "news signal" in result[0]["reasoning"]


def test_buy_and_sell_same_coin_not_merged():
    sigs = [_sig("DOGE", action="buy"), _sig("DOGE", action="sell")]
    result = deduplicate(sigs)
    assert len(result) == 2


def test_coin_name_normalised_to_upper():
    sigs = [_sig("doge"), _sig("DOGE")]
    result = deduplicate(sigs)
    assert len(result) == 1
    assert result[0]["coin"] == "DOGE"


def test_empty_input():
    assert deduplicate([]) == []


def test_three_dupes_merged_to_one_with_max_confidence():
    sigs = [
        _sig("PEPE", confidence=0.70),
        _sig("PEPE", confidence=0.85),
        _sig("PEPE", confidence=0.78),
    ]
    result = deduplicate(sigs)
    assert len(result) == 1
    assert result[0]["confidence"] == 0.85
