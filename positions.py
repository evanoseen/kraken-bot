from __future__ import annotations

import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

POSITIONS_FILE = "positions.json"


def load_positions() -> dict:
    """Load tracked buy positions from disk."""
    if not os.path.exists(POSITIONS_FILE):
        return {}
    try:
        with open(POSITIONS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_positions(positions: dict):
    try:
        with open(POSITIONS_FILE, "w") as f:
            json.dump(positions, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save positions: {e}")


def record_buy(coin: str, price: float, amount_cad: float):
    """Record a new buy position."""
    positions = load_positions()
    positions[coin] = {
        "entry_price": price,
        "amount_cad": amount_cad,
        "timestamp": datetime.utcnow().isoformat(),
    }
    save_positions(positions)
    logger.info(f"Position recorded: {coin} @ ${price:.8f} (${amount_cad:.2f} CAD)")


def remove_position(coin: str):
    """Remove a position after selling."""
    positions = load_positions()
    positions.pop(coin, None)
    save_positions(positions)


def get_position(coin: str) -> dict | None:
    return load_positions().get(coin)


TRADES_CSV = "trades.csv"
TRADES_JSONL = "trades.jsonl"


def log_trade(
    coin: str,
    action: str,
    price: float,
    amount_cad: float,
    pnl: Optional[float] = None,
    *,
    pair: Optional[str] = None,
    order_id: Optional[str] = None,
) -> None:
    """Append a trade event to both `trades.csv` (legacy) and `trades.jsonl` (Day 20 structured).

    `action` is decomposed into `side` (`buy`/`sell`) and `signal_source`
    (`newlisting`, `signal`, `stoploss`, `takeprofit`) so the JSONL is queryable
    by either axis. `pair` and `order_id` are optional kwargs — callers that
    have them should pass them through; trader.py's existing call sites pass
    `None` and downstream JSONL queries will see `null`.
    """
    timestamp = datetime.utcnow().isoformat()

    # Legacy CSV — keep writing so existing tooling (daily_pnl.py once Day 23
    # lands, etc.) doesn't break.
    try:
        write_header = not os.path.exists(TRADES_CSV)
        with open(TRADES_CSV, "a") as f:
            if write_header:
                f.write("timestamp,coin,action,price,amount_cad,pnl_cad\n")
            pnl_str = f"{pnl:.2f}" if pnl is not None else ""
            f.write(
                f"{timestamp},"
                f"{coin},{action},{price:.8f},"
                f"{amount_cad:.2f},{pnl_str}\n"
            )
    except Exception as e:
        logger.error(f"Failed to log trade CSV: {e}")

    # Day 20 structured JSONL — one JSON object per line, queryable with jq.
    try:
        if "_" in action:
            side, signal_source = action.split("_", 1)
        else:
            side, signal_source = action, "unknown"
        volume = round(amount_cad / price, 8) if price > 0 else 0.0
        event = {
            "timestamp": timestamp,
            "coin": coin,
            "pair": pair,
            "side": side,
            "signal_source": signal_source,
            "volume": volume,
            "price": price,
            "amount_cad": amount_cad,
            "pnl_cad": pnl,
            "order_id": order_id,
        }
        with open(TRADES_JSONL, "a") as f:
            f.write(json.dumps(event) + "\n")
    except Exception as e:
        logger.error(f"Failed to log trade JSONL: {e}")
