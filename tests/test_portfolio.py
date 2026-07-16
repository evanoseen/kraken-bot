"""Tests for Day 49 — portfolio value calculator."""
from __future__ import annotations

import logging
import pytest
from unittest.mock import MagicMock
from portfolio import compute_value


def test_no_holdings_returns_balance():
    client = MagicMock()
    assert compute_value(client, {}, 100.0) == 100.0


def test_single_position_added():
    client = MagicMock()
    get_price = MagicMock(return_value=0.10)
    # 500 DOGE @ $0.10 = $50 + $100 cash = $150
    result = compute_value(client, {"DOGE": 500.0}, 100.0, get_price_fn=get_price)
    assert result == pytest.approx(150.0)


def test_multiple_positions_summed():
    client = MagicMock()
    prices = {"DOGE": 0.10, "SHIB": 0.00002}

    def get_price(c, coin):
        return prices[coin]

    # 500 DOGE = $50, 1_000_000 SHIB = $20, cash = $30 → total = $100
    result = compute_value(
        client,
        {"DOGE": 500.0, "SHIB": 1_000_000.0},
        30.0,
        get_price_fn=get_price,
    )
    assert result == pytest.approx(100.0)


def test_failed_price_fetch_excluded(caplog):
    client = MagicMock()

    def get_price(c, coin):
        raise ConnectionError("timeout")

    with caplog.at_level(logging.WARNING, logger="portfolio"):
        result = compute_value(client, {"DOGE": 500.0}, 100.0, get_price_fn=get_price)

    assert result == pytest.approx(100.0)
    assert "excluded" in caplog.text


def test_none_price_excluded(caplog):
    client = MagicMock()
    get_price = MagicMock(return_value=None)

    with caplog.at_level(logging.WARNING, logger="portfolio"):
        result = compute_value(client, {"DOGE": 500.0}, 100.0, get_price_fn=get_price)

    assert result == pytest.approx(100.0)
    assert "excluded" in caplog.text


def test_partial_failure_uses_successful_prices():
    client = MagicMock()
    prices = {"DOGE": 0.10}

    def get_price(c, coin):
        if coin not in prices:
            raise RuntimeError("no price")
        return prices[coin]

    # DOGE: 500 * 0.10 = $50; BTC fails → $0; cash = $100 → total = $150
    result = compute_value(
        client,
        {"DOGE": 500.0, "BTC": 0.001},
        100.0,
        get_price_fn=get_price,
    )
    assert result == pytest.approx(150.0)


def test_empty_holdings_no_price_calls():
    client = MagicMock()
    get_price = MagicMock()
    compute_value(client, {}, 50.0, get_price_fn=get_price)
    get_price.assert_not_called()
