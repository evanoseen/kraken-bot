"""Telegram trade alert notifier (Day 26).

Sends a message to a Telegram chat whenever a real trade executes.
Fail-soft: if the token is unset or the request fails, the bot continues
normally — a notification outage must never halt trading.

Usage:
    from notifier import notify_trade
    notify_trade("buy", "DOGE", 12.50, 0.0823, confidence=0.88)
    notify_trade("sell_stoploss", "DOGE", 11.20, 0.0741, pnl=-1.30)

Environment variables (optional — notifications are simply skipped if absent):
    TELEGRAM_BOT_TOKEN  — bot token from @BotFather
    TELEGRAM_CHAT_ID    — numeric chat / channel ID to send to
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

_API_URL = "https://api.telegram.org/bot{token}/sendMessage"
_TIMEOUT = 5  # seconds


def _token() -> Optional[str]:
    return os.getenv("TELEGRAM_BOT_TOKEN")


def _chat_id() -> Optional[str]:
    return os.getenv("TELEGRAM_CHAT_ID")


def _build_message(
    action: str,
    coin: str,
    amount_cad: float,
    price: float,
    confidence: Optional[float],
    pnl: Optional[float],
    dry_run: bool,
) -> str:
    icons = {
        "buy": "BUY",
        "buy_signal": "BUY",
        "buy_newlisting": "NEW LISTING BUY",
        "sell": "SELL",
        "sell_signal": "SELL",
        "sell_stoploss": "STOP-LOSS",
        "sell_takeprofit": "TAKE-PROFIT",
        "sell_stale": "STALE EXIT",
        "balance_alert": "LOW BALANCE WARNING",
    }
    label = icons.get(action, action.upper())
    prefix = "[DRY RUN] " if dry_run else ""
    lines = [
        f"{prefix}{label} {coin}",
        f"Amount: ${amount_cad:.2f} CAD @ ${price:.8f}",
    ]
    if confidence is not None:
        lines.append(f"Confidence: {confidence:.0%}")
    if pnl is not None:
        if pnl >= 0:
            lines.append(f"P&L: +${pnl:.2f} CAD")
        else:
            lines.append(f"P&L: -${abs(pnl):.2f} CAD")
    return "\n".join(lines)


def notify_trade(
    action: str,
    coin: str,
    amount_cad: float,
    price: float,
    *,
    confidence: Optional[float] = None,
    pnl: Optional[float] = None,
    dry_run: bool = False,
) -> None:
    token = _token()
    chat_id = _chat_id()
    if not token or not chat_id:
        return

    text = _build_message(action, coin, amount_cad, price, confidence, pnl, dry_run)
    try:
        resp = requests.post(
            _API_URL.format(token=token),
            json={"chat_id": chat_id, "text": text},
            timeout=_TIMEOUT,
        )
        if not resp.ok:
            logger.warning("Telegram alert failed (%s): %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("Telegram alert error (non-fatal): %s", exc)
