"""CSV trade log (Day 42).

Appends every executed trade to a CSV file for post-session analysis.
Creates the file with a header row on first write. Fail-soft: a write
error is logged as a warning and never halts the bot.

Usage:
    from trade_logger import append_trade
    append_trade("DOGE", "buy", 12.50, 0.0823, confidence=0.88)
    append_trade("DOGE", "sell_stoploss", 11.20, 0.0741, pnl=-1.30)

Set TRADE_LOG_PATH in .env to override the default path (trades.csv).
"""
from __future__ import annotations

import csv
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_HEADERS = ["timestamp", "coin", "action", "amount_cad", "price", "confidence", "pnl"]


def _log_path() -> Path:
    return Path(os.getenv("TRADE_LOG_PATH", "trades.csv"))


def append_trade(
    coin: str,
    action: str,
    amount_cad: float,
    price: float,
    *,
    confidence: Optional[float] = None,
    pnl: Optional[float] = None,
) -> None:
    path = _log_path()
    try:
        write_header = not path.exists() or path.stat().st_size == 0
        with path.open("a", newline="") as f:
            writer = csv.writer(f)
            if write_header:
                writer.writerow(_HEADERS)
            writer.writerow([
                datetime.now(timezone.utc).isoformat(),
                coin.upper(),
                action,
                f"{amount_cad:.4f}",
                f"{price:.8f}",
                f"{confidence:.4f}" if confidence is not None else "",
                f"{pnl:.4f}" if pnl is not None else "",
            ])
    except Exception as exc:
        logger.warning("trade_logger: failed to write to %s: %s", path, exc)
