"""Locks the Day 17 Config dataclass contract.

Pins:
1. `Config` is a frozen dataclass exported from `config`.
2. `Config.from_env()` produces a populated instance.
3. The module-level `cfg` singleton is an instance of `Config`.
4. Every env var the bot used to read as a module global is now a field
   on the dataclass — no field name drift on future env-var additions.
5. Mutation attempts on a frozen instance raise `FrozenInstanceError`.
"""
from __future__ import annotations

import dataclasses

import pytest


EXPECTED_FIELDS = {
    "kraken_api_key",
    "kraken_private_key",
    "anthropic_api_key",
    "max_trade_amount",
    "min_confidence",
    "daily_loss_limit",
    "stop_loss_pct",
    "take_profit_pct",
    "run_interval_minutes",
    "dry_run",
    "max_drawdown_pct",
    "max_open_positions",
    "max_position_age_hours",
    "max_trades_per_coin",
    "max_trades_per_day",
    "min_balance_reserve",
    "min_hold_minutes",
    "min_trade_amount",
    "profit_target",
    "trade_cooldown_minutes",
    "balance_alert_threshold",
    "telegram_bot_token",
    "telegram_chat_id",
}


def test_config_is_a_frozen_dataclass():
    """Config is a dataclass and the frozen flag is set."""
    from config import Config

    assert dataclasses.is_dataclass(Config)
    # Frozen flag lives in __dataclass_params__
    assert Config.__dataclass_params__.frozen is True


def test_config_from_env_returns_instance():
    """Done-when probe verbatim: from config import Config; c = Config.from_env() works."""
    from config import Config

    c = Config.from_env()
    assert isinstance(c, Config)


def test_module_singleton_cfg_is_a_config():
    """The convenience singleton `cfg` is a Config instance."""
    import config

    assert isinstance(config.cfg, config.Config)


def test_every_expected_field_is_present():
    """All env vars the bot used to read as globals are now Config fields."""
    from config import Config

    field_names = {f.name for f in dataclasses.fields(Config)}
    missing = EXPECTED_FIELDS - field_names
    extra = field_names - EXPECTED_FIELDS

    assert not missing, f"Missing fields on Config: {sorted(missing)}"
    assert not extra, f"Unexpected fields on Config: {sorted(extra)}"


def test_field_types_match_intent():
    """Numeric tunables are float/int, secrets are Optional[str], dry_run is bool."""
    from config import Config

    by_name = {f.name: f.type for f in dataclasses.fields(Config)}
    # `f.type` is a string (forward-evaluated) under `from __future__ import annotations`
    assert "Optional[str]" in by_name["kraken_api_key"]
    assert "Optional[str]" in by_name["kraken_private_key"]
    assert "Optional[str]" in by_name["anthropic_api_key"]
    assert "float" in by_name["max_trade_amount"]
    assert "float" in by_name["min_confidence"]
    assert "float" in by_name["daily_loss_limit"]
    assert "float" in by_name["stop_loss_pct"]
    assert "float" in by_name["take_profit_pct"]
    assert "int" in by_name["run_interval_minutes"]
    assert "bool" in by_name["dry_run"]


def test_frozen_blocks_mutation():
    """Setting any attribute on a frozen Config raises FrozenInstanceError."""
    from config import Config

    c = Config.from_env()
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.max_trade_amount = 999.0  # type: ignore[misc]
