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
    profit_target: Optional[float]
    max_trades_per_coin: Optional[int]
    min_balance_reserve: float

    # Risk caps
    max_trade_amount: float
    min_trade_amount: float
    min_confidence: float
    daily_loss_limit: float
    max_drawdown_pct: float
    max_open_positions: int
    max_trades_per_day: int

    # Exit thresholds
    stop_loss_pct: float
    take_profit_pct: float
    max_position_age_hours: float
    min_hold_minutes: float
    trailing_stop_pct: Optional[float]

    # Cadence
    run_interval_minutes: int
    trade_cooldown_minutes: float

    # Master switch
    dry_run: bool

    def validate(self) -> None:
        """Raise ValueError if any tunable is out of range or contradictory (Day 73).

        `from_env()` casts every value to its declared type, but casting
        doesn't catch nonsense — `MIN_TRADE_AMOUNT > MAX_TRADE_AMOUNT` loads
        fine and then silently produces a broken `size_position()` curve;
        a negative `STOP_LOSS_PCT` loads fine and then never triggers.
        Collects every violation instead of raising on the first one, so a
        misconfigured `.env` gets fixed in one pass instead of one error at
        a time. Called from `health.run_checks()` at startup, before any
        trading cycle runs.
        """
        errors: list[str] = []

        if self.min_trade_amount <= 0:
            errors.append(f"MIN_TRADE_AMOUNT must be > 0 (got {self.min_trade_amount})")
        if self.max_trade_amount <= 0:
            errors.append(f"MAX_TRADE_AMOUNT must be > 0 (got {self.max_trade_amount})")
        if self.min_trade_amount > self.max_trade_amount:
            errors.append(
                f"MIN_TRADE_AMOUNT ({self.min_trade_amount}) must be <= "
                f"MAX_TRADE_AMOUNT ({self.max_trade_amount})"
            )
        if not (0.0 <= self.min_confidence <= 1.0):
            errors.append(f"MIN_CONFIDENCE must be between 0 and 1 (got {self.min_confidence})")
        if self.daily_loss_limit <= 0:
            errors.append(f"DAILY_LOSS_LIMIT must be > 0 (got {self.daily_loss_limit})")
        if not (0.0 < self.max_drawdown_pct <= 1.0):
            errors.append(f"MAX_DRAWDOWN_PCT must be between 0 (exclusive) and 1 (got {self.max_drawdown_pct})")
        if self.max_open_positions <= 0:
            errors.append(f"MAX_OPEN_POSITIONS must be > 0 (got {self.max_open_positions})")
        if self.max_trades_per_day <= 0:
            errors.append(f"MAX_TRADES_PER_DAY must be > 0 (got {self.max_trades_per_day})")
        if not (0.0 < self.stop_loss_pct <= 1.0):
            errors.append(f"STOP_LOSS_PCT must be between 0 (exclusive) and 1 (got {self.stop_loss_pct})")
        if self.take_profit_pct <= 0:
            errors.append(f"TAKE_PROFIT_PCT must be > 0 (got {self.take_profit_pct})")
        if self.max_position_age_hours <= 0:
            errors.append(f"MAX_POSITION_AGE_HOURS must be > 0 (got {self.max_position_age_hours})")
        if self.min_hold_minutes < 0:
            errors.append(f"MIN_HOLD_MINUTES must be >= 0 (got {self.min_hold_minutes})")
        if self.run_interval_minutes <= 0:
            errors.append(f"RUN_INTERVAL_MINUTES must be > 0 (got {self.run_interval_minutes})")
        if self.trade_cooldown_minutes < 0:
            errors.append(f"TRADE_COOLDOWN_MINUTES must be >= 0 (got {self.trade_cooldown_minutes})")
        if self.min_balance_reserve < 0:
            errors.append(f"MIN_BALANCE_RESERVE must be >= 0 (got {self.min_balance_reserve})")
        if self.trailing_stop_pct is not None and not (0.0 < self.trailing_stop_pct <= 1.0):
            errors.append(
                f"TRAILING_STOP_PCT must be between 0 (exclusive) and 1 if set (got {self.trailing_stop_pct})"
            )
        if self.profit_target is not None and self.profit_target <= 0:
            errors.append(f"PROFIT_TARGET must be > 0 if set (got {self.profit_target})")
        if self.balance_alert_threshold is not None and self.balance_alert_threshold < 0:
            errors.append(f"BALANCE_ALERT_THRESHOLD must be >= 0 if set (got {self.balance_alert_threshold})")
        if self.max_trades_per_coin is not None and self.max_trades_per_coin <= 0:
            errors.append(f"MAX_TRADES_PER_COIN must be > 0 if set (got {self.max_trades_per_coin})")

        if errors:
            raise ValueError("Invalid configuration:\n  " + "\n  ".join(errors))

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
            balance_alert_threshold=float(v) if (v := os.getenv("BALANCE_ALERT_THRESHOLD")) else None,
            profit_target=float(v) if (v := os.getenv("PROFIT_TARGET")) else None,
            max_trades_per_coin=int(v) if (v := os.getenv("MAX_TRADES_PER_COIN")) else None,
            min_balance_reserve=float(os.getenv("MIN_BALANCE_RESERVE", "0.0")),
            max_trade_amount=float(os.getenv("MAX_TRADE_AMOUNT", "25.0")),
            min_trade_amount=float(os.getenv("MIN_TRADE_AMOUNT", "1.0")),
            min_confidence=float(os.getenv("MIN_CONFIDENCE", "0.80")),
            daily_loss_limit=float(os.getenv("DAILY_LOSS_LIMIT", "50.0")),
            max_drawdown_pct=float(os.getenv("MAX_DRAWDOWN_PCT", "0.20")),
            max_open_positions=int(os.getenv("MAX_OPEN_POSITIONS", "3")),
            max_trades_per_day=int(os.getenv("MAX_TRADES_PER_DAY", "10")),
            stop_loss_pct=float(os.getenv("STOP_LOSS_PCT", "0.10")),
            take_profit_pct=float(os.getenv("TAKE_PROFIT_PCT", "0.25")),
            max_position_age_hours=float(os.getenv("MAX_POSITION_AGE_HOURS", "24")),
            min_hold_minutes=float(os.getenv("MIN_HOLD_MINUTES", "0")),
            trailing_stop_pct=float(v) if (v := os.getenv("TRAILING_STOP_PCT")) else None,
            run_interval_minutes=int(os.getenv("RUN_INTERVAL_MINUTES", "15")),
            trade_cooldown_minutes=float(os.getenv("TRADE_COOLDOWN_MINUTES", "60")),
            dry_run=os.getenv("DRY_RUN", "true").lower() == "true",
        )


# Module-level singleton for caller ergonomics.
cfg: Config = Config.from_env()
