"""Entry point for the Kraken meme coin trading bot.

CLI flags:
  --once      Run one cycle then exit cleanly (skips the scheduler).
              Good for manual runs, cron jobs, and testing.
  --dry-run   Force DRY_RUN=true regardless of the .env value.
              The bot never places a real order with this flag active.

Local imports (trader, heartbeat, config) are deferred to inside main() so
--dry-run can set os.environ["DRY_RUN"] before Config.from_env() reads it.
Module-style imports (import trader) — not from-imports — are used so that
mocker.patch("trader.run_trading_cycle") works correctly in tests.
"""
from __future__ import annotations

import argparse
import logging
import os
import signal
import time
from logging.handlers import RotatingFileHandler
from typing import Optional

# bot.log has grown unbounded since Day 1 on a 24/7 VPS — cap it at 5MB with
# 5 rotated backups (~30MB ceiling) instead of letting it grow forever.
LOG_MAX_BYTES = 5 * 1024 * 1024
LOG_BACKUP_COUNT = 5


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="kraken-bot",
        description="Kraken meme coin trading bot",
    )
    p.add_argument(
        "--once",
        action="store_true",
        help="Run one cycle then exit (skips the scheduler)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Force DRY_RUN=true regardless of .env — never places real orders",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    # Set before local imports so Config.from_env() picks it up.
    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    # Deferred so --dry-run is in the environment before Config.from_env() runs.
    # Module-style imports keep patching targets stable (mocker.patch works on
    # module attributes, not on names already bound via `from x import y`).
    import schedule
    import heartbeat
    import health
    import notifier
    import trader
    from config import cfg

    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            RotatingFileHandler("bot.log", maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT),
        ],
    )
    logger = logging.getLogger(__name__)

    if args.dry_run:
        logger.info("--dry-run flag: forcing DRY_RUN=true, no real orders will be placed")
    if args.once:
        logger.info("--once flag: running a single cycle then exiting")

    logger.info("Kraken Meme Coin NewsTrader starting...")
    health.run_checks(cfg)

    def _shutdown(signum: int, _frame: object) -> None:
        sig_name = signal.Signals(signum).name
        logger.info(f"Received {sig_name} — shutting down gracefully...")
        w, l = trader._wins, trader._losses
        total = w + l
        win_rate = f"{w / total * 100:.0f}%" if total else "n/a"
        logger.info(
            f"Session summary: {trader._trades_today} trade(s) | "
            f"W/L {w}/{l} ({win_rate}) | "
            f"started at ${trader._starting_balance:.2f} CAD"
            if trader._starting_balance else
            f"Session summary: {trader._trades_today} trade(s) | W/L {w}/{l} ({win_rate})"
        )
        notifier.notify_shutdown(trader._trades_today, w, l, trader._starting_balance, sig_name)
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    def run_cycle() -> None:
        trader.run_trading_cycle()
        heartbeat.write_heartbeat()

    run_cycle()

    if args.once:
        logger.info("--once: single cycle complete, exiting with code 0")
        return 0

    schedule.every(cfg.run_interval_minutes).minutes.do(run_cycle)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
