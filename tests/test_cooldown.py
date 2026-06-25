"""Tests for Day 29 — per-coin trade cooldown."""
from __future__ import annotations

import pytest
import cooldown


@pytest.fixture(autouse=True)
def reset():
    cooldown.reset()
    yield
    cooldown.reset()


def test_not_on_cooldown_initially():
    assert not cooldown.is_on_cooldown("DOGE", 60)


def test_on_cooldown_immediately_after_trade():
    cooldown.mark_traded("DOGE")
    assert cooldown.is_on_cooldown("DOGE", 60)


def test_cooldown_expires(monkeypatch):
    import time
    start = time.monotonic()
    monkeypatch.setattr("cooldown.time.monotonic", lambda: start)
    cooldown.mark_traded("DOGE")
    monkeypatch.setattr("cooldown.time.monotonic", lambda: start + 61 * 60)
    assert not cooldown.is_on_cooldown("DOGE", 60)


def test_cooldown_still_active_before_expiry(monkeypatch):
    import time
    start = time.monotonic()
    monkeypatch.setattr("cooldown.time.monotonic", lambda: start)
    cooldown.mark_traded("DOGE")
    monkeypatch.setattr("cooldown.time.monotonic", lambda: start + 59 * 60)
    assert cooldown.is_on_cooldown("DOGE", 60)


def test_cooldown_is_per_coin():
    cooldown.mark_traded("DOGE")
    assert not cooldown.is_on_cooldown("SHIB", 60)


def test_reset_clears_all():
    cooldown.mark_traded("DOGE")
    cooldown.mark_traded("SHIB")
    cooldown.reset()
    assert not cooldown.is_on_cooldown("DOGE", 60)
    assert not cooldown.is_on_cooldown("SHIB", 60)


def test_coin_name_case_insensitive():
    cooldown.mark_traded("doge")
    assert cooldown.is_on_cooldown("DOGE", 60)
