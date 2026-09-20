"""Portfolio value calculator (Day 49).

Computes the total session value: CAD balance plus the current market
value of every open position. This gives a more accurate P&L than the
cash balance alone, which drops every time you buy and rises only on sell.

Usage:
    from portfolio import compute_value
    total = compute_value(client, holdings, balance)
    logger.info(f"Portfolio: ${total:.2f} CAD")

If a price fetch fails for a coin, that position is valued at 0 and a
warning is logged — the function never raises.
"""
from __future__ import annotations

import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


def compute_value(
    client: object,
    holdings: dict[str, float],
    balance: float,
    get_price_fn: Optional[Callable[[object, str], Optional[float]]] = None,
) -> float:
    resolver: Callable[[object, str], Optional[float]]
    if get_price_fn is None:
        from kraken_client import get_price as resolver
    else:
        resolver = get_price_fn

    position_value = 0.0
    for coin, amount in holdings.items():
        try:
            price: Optional[float] = resolver(client, coin)
            if price:
                position_value += amount * price
            else:
                logger.warning("portfolio: no price for %s — excluded from value", coin)
        except Exception as exc:
            logger.warning("portfolio: price fetch failed for %s: %s — excluded", coin, exc)

    return balance + position_value
