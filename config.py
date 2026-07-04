"""All bot configuration as a single frozen dataclass.

Day 17 extracted env-var reading from module-level globals into a `Config`
dataclass. Two access patterns:

  Recommended (convenience, module-load):
      from config import cfg
      use(cfg.max_trade_amount)

  Explicit (preferred for tests):
      from config import Config
      c = Config.from_env()
      use(c.max_trade_amount)

The frozen dataclass gives attribute access + type safety + repr without
risking mid-cycle mutation of a tunable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Every environment variable the bot reads, in one place.

    Secrets are Optional[str] because they may be unset at construction time
    (CI placeholders, tests). The bot's first private REST call is when a
    real key actually matters; until then None is permissible.
    """

    # Secrets
    kraken_api_key: Optional[str]
    kraken_private_key: Optional[str]
    anthropic_api_key: Optional[str]
    telegram_bot_token: Optional[str]
    telegram_chat_id: Optional[str]
    balance_alert_threshold: Optional[float]

    # Risk caps
    max_trade_amount: float
    min_confidence: float
    daily_loss_limit: float
    max_drawdown_pct: float
    max_open_positions: int
    max_trades_per_day: int

    # Exit thresholds
    stop_loss_pct: float
    take_profit_pct: float
    max_position_age_hours: float

    # Cadence
    run_interval_minutes: int
    trade_cooldown_minutes: float

    # Master switch
    dry_run: bool

    @classmethod
    def from_env(cls) -> "Config":
        """Load every field from the process environment, falling back to .env via dotenv."""
        load_dotenv()
        return cls(
            kraken_api_key=os.getenv("KRAKEN_API_KEY"),
            kraken_private_key=os.getenv("KRAKEN_PRIVATE_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN"),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID"),
            balance_alert_threshold=float(os.getenv("BALANCE_ALERT_THRESHOLD")) if os.getenv("BALANCE_ALERT_THRESHOLD") else None,
            max_trade_amount=float(os.getenv("MAX_TRADE_AMOUNT", "25.0")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.80")),
            daily_loss_limit=float(os.getenv("DAILY_LOSS_LIMIT", "50.0")),
            max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.20")),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "3")),
            max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "10")),
            stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.10")),
            take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "0.25")),
            max_position_age_hours=float(os.getenv("MAX_POSITION_AGE_HOURS", "24")),
            run_interval_minutes=int(os.getenv("RUN_INTERVAL_MINUTES", "15")),
            trade_cooldown_minutes=float(os.getenv("TRADE_COOLDOWN_MINUTES", "60")),
            dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        )


# Module-level singleton for caller ergonomics.
cfg: Config = Config.from_env()
