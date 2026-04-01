import json
import os
import logging
from datetime import datetime

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


def log_trade(coin: str, action: str, price: float, amount_cad: float, pnl: float = None):
    """Append a trade to trades.csv."""
    try:
        write_header = not os.path.exists("trades.csv")
        with open("trades.csv", "a") as f:
            if write_header:
                f.write("timestamp,coin,action,price,amount_cad,pnl_cad\n")
            pnl_str = f"{pnl:.2f}" if pnl is not None else ""
            f.write(
                f"{datetime.utcnow().isoformat()},"
                f"{coin},{action},{price:.8f},"
                f"{amount_cad:.2f},{pnl_str}\n"
            )
    except Exception as e:
        logger.error(f"Failed to log trade: {e}")
