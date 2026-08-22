"""Startup health check (Day 30).

Call run_checks() once before the first trading cycle. It validates that
required env vars are set, that Kraken's public API is reachable, and then
logs a formatted config summary so every bot run begins with a clear picture
of what it is configured to do.

Raises SystemExit(1) on a fatal misconfiguration so the problem is obvious
immediately rather than surfacing as a cryptic error mid-cycle.
"""
from __future__ import annotations

import logging
import sys

import requests

logger = logging.getLogger(__name__)

_KRAKEN_PING_URL = "https://api.kraken.com/0/public/Time"
_TIMEOUT = 5

_REQUIRED_VARS = [
    ("KRAKEN_API_KEY", "kraken_api_key"),
    ("KRAKEN_PRIVATE_KEY", "kraken_private_key"),
    ("ANTHROPIC_API_KEY", "anthropic_api_key"),
]


def _check_env(cfg) -> list[str]:
    missing = []
    for env_name, attr in _REQUIRED_VARS:
        if not getattr(cfg, attr):
            missing.append(env_name)
    return missing


def _check_kraken_connectivity() -> bool:
    try:
        resp = requests.get(_KRAKEN_PING_URL, timeout=_TIMEOUT)
        return resp.ok and not resp.json().get("error")
    except Exception:
        return False


def _log_banner(cfg) -> None:
    dry = "[DRY RUN] " if cfg.dry_run else ""
    lines = [
        "=" * 55,
        f"  {dry}KRAKEN BOT READY",
        "=" * 55,
        f"  interval        {cfg.run_interval_minutes}m",
        f"  max trade       ${cfg.max_trade_amount:.2f} CAD",
        f"  min confidence  {cfg.min_confidence:.0%}",
        f"  daily loss cap  ${cfg.daily_loss_limit:.2f} CAD",
        f"  max drawdown    {cfg.max_drawdown_pct:.0%}",
        f"  max positions   {cfg.max_open_positions}",
        f"  cooldown        {cfg.trade_cooldown_minutes:.0f}m",
        f"  stop-loss       {cfg.stop_loss_pct:.0%}",
        f"  take-profit     {cfg.take_profit_pct:.0%}",
        f"  telegram        {'on' if cfg.telegram_bot_token else 'off'}",
        "=" * 55,
    ]
    for line in lines:
        logger.info(line)


def run_checks(cfg) -> None:
    missing = _check_env(cfg)
    if missing:
        logger.error("Missing required env vars: %s", ", ".join(missing))
        logger.error("Set them in .env and restart the bot.")
        sys.exit(1)

    try:
        cfg.validate()
    except ValueError as exc:
        logger.error(str(exc))
        logger.error("Fix these in .env and restart the bot.")
        sys.exit(1)

    logger.info("Checking Kraken connectivity...")
    if _check_kraken_connectivity():
        logger.info("Kraken API reachable.")
    else:
        logger.warning("Kraken API ping failed — check your network. Continuing anyway.")

    _log_banner(cfg)
