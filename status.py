"""Cycle status file (Day 45).

Writes a JSON snapshot of bot state after every trading cycle. External
tools (cron checks, dashboards, uptime monitors) can read this file
instead of parsing logs.

Usage:
    from status import write_status
    write_status(balance=105.20, open_positions=2, trades_today=3, wins=2, losses=1)

Set STATUS_FILE in .env to override the default path (status.json).
Fail-soft: a write error is logged as a warning and never halts the bot.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def _status_path() -> Path:
    return Path(os.getenv("STATUS_FILE", "status.json"))


def write_status(
    *,
    balance: float,
    open_positions: int,
    trades_today: int,
    wins: int,
    losses: int,
    starting_balance: Optional[float] = None,
) -> None:
    total = wins + losses
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "balance_cad": round(balance, 4),
        "starting_balance_cad": round(starting_balance, 4) if starting_balance is not None else None,
        "session_pnl_cad": round(balance - starting_balance, 4) if starting_balance is not None else None,
        "open_positions": open_positions,
        "trades_today": trades_today,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / total, 4) if total else None,
    }
    path = _status_path()
    try:
        path.write_text(json.dumps(payload, indent=2))
    except Exception as exc:
        logger.warning("status: failed to write %s: %s", path, exc)
