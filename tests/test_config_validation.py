"""Tests for Day 73 — Config.validate() and its wiring into health.run_checks().

`Config.from_env()` casts every env var to its declared type but never
checked whether the *values* made sense — a misconfigured .env loaded
silently and failed confusingly downstream instead of failing loud at
startup. These tests use a real, valid `Config` from `Config.from_env()`
as a base and `dataclasses.replace()` to introduce one violation at a
time, rather than a mock — `validate()` is real logic on a real dataclass,
not something worth faking.
"""
from __future__ import annotations

import dataclasses

import pytest
from config import Config


@pytest.fixture
def valid_cfg(monkeypatch) -> Config:
    monkeypatch.setenv("KRAKEN_API_KEY", "k")
    monkeypatch.setenv("KRAKEN_PRIVATE_KEY", "p")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "a")
    return Config.from_env()


def test_valid_config_does_not_raise(valid_cfg):
    valid_cfg.validate()  # should not raise


def test_min_trade_amount_above_max_raises(valid_cfg):
    """The literal Day 73 done-when."""
    bad = dataclasses.replace(valid_cfg, min_trade_amount=50.0, max_trade_amount=25.0)
    with pytest.raises(ValueError, match="MIN_TRADE_AMOUNT.*MAX_TRADE_AMOUNT"):
        bad.validate()


@pytest.mark.parametrize("field,value", [
    ("min_trade_amount", 0.0),
    ("min_trade_amount", -1.0),
    ("max_trade_amount", 0.0),
    ("max_trade_amount", -1.0),
    ("daily_loss_limit", 0.0),
    ("daily_loss_limit", -50.0),
    ("max_open_positions", 0),
    ("max_open_positions", -1),
    ("max_trades_per_day", 0),
    ("max_position_age_hours", 0.0),
    ("max_position_age_hours", -24.0),
    ("min_hold_minutes", -1.0),
    ("run_interval_minutes", 0),
    ("run_interval_minutes", -15),
    ("trade_cooldown_minutes", -1.0),
    ("min_balance_reserve", -10.0),
    ("take_profit_pct", 0.0),
    ("take_profit_pct", -0.25),
])
def test_out_of_range_scalar_raises(valid_cfg, field, value):
    bad = dataclasses.replace(valid_cfg, **{field: value})
    with pytest.raises(ValueError):
        bad.validate()


@pytest.mark.parametrize("value", [-0.1, 1.1, 2.0])
def test_min_confidence_out_of_unit_range_raises(valid_cfg, value):
    bad = dataclasses.replace(valid_cfg, min_confidence=value)
    with pytest.raises(ValueError, match="MIN_CONFIDENCE"):
        bad.validate()


@pytest.mark.parametrize("value", [0.0, 1.1, -0.1])
def test_max_drawdown_pct_out_of_range_raises(valid_cfg, value):
    bad = dataclasses.replace(valid_cfg, max_drawdown_pct=value)
    with pytest.raises(ValueError, match="MAX_DRAWDOWN_PCT"):
        bad.validate()


@pytest.mark.parametrize("value", [0.0, 1.1, -0.05])
def test_stop_loss_pct_out_of_range_raises(valid_cfg, value):
    bad = dataclasses.replace(valid_cfg, stop_loss_pct=value)
    with pytest.raises(ValueError, match="STOP_LOSS_PCT"):
        bad.validate()


def test_min_confidence_boundaries_are_valid(valid_cfg):
    dataclasses.replace(valid_cfg, min_confidence=0.0).validate()
    dataclasses.replace(valid_cfg, min_confidence=1.0).validate()


# ── Optional fields: None is always fine; a set value must be sane ─────────

def test_trailing_stop_pct_none_is_valid(valid_cfg):
    dataclasses.replace(valid_cfg, trailing_stop_pct=None).validate()


@pytest.mark.parametrize("value", [0.0, -0.1, 1.5])
def test_trailing_stop_pct_out_of_range_raises(valid_cfg, value):
    bad = dataclasses.replace(valid_cfg, trailing_stop_pct=value)
    with pytest.raises(ValueError, match="TRAILING_STOP_PCT"):
        bad.validate()


def test_profit_target_none_is_valid(valid_cfg):
    dataclasses.replace(valid_cfg, profit_target=None).validate()


def test_profit_target_negative_raises(valid_cfg):
    bad = dataclasses.replace(valid_cfg, profit_target=-10.0)
    with pytest.raises(ValueError, match="PROFIT_TARGET"):
        bad.validate()


def test_balance_alert_threshold_negative_raises(valid_cfg):
    bad = dataclasses.replace(valid_cfg, balance_alert_threshold=-5.0)
    with pytest.raises(ValueError, match="BALANCE_ALERT_THRESHOLD"):
        bad.validate()


def test_balance_alert_threshold_zero_is_valid(valid_cfg):
    dataclasses.replace(valid_cfg, balance_alert_threshold=0.0).validate()


def test_max_trades_per_coin_zero_raises(valid_cfg):
    bad = dataclasses.replace(valid_cfg, max_trades_per_coin=0)
    with pytest.raises(ValueError, match="MAX_TRADES_PER_COIN"):
        bad.validate()


def test_max_trades_per_coin_none_is_valid(valid_cfg):
    dataclasses.replace(valid_cfg, max_trades_per_coin=None).validate()


def test_multiple_violations_are_all_collected_in_one_error(valid_cfg):
    """A misconfigured .env should be fixable in one pass, not one error
    per restart."""
    bad = dataclasses.replace(
        valid_cfg,
        min_trade_amount=100.0,
        max_trade_amount=10.0,
        min_confidence=5.0,
        stop_loss_pct=-0.1,
    )
    with pytest.raises(ValueError) as exc_info:
        bad.validate()
    message = str(exc_info.value)
    assert "MIN_TRADE_AMOUNT" in message
    assert "MIN_CONFIDENCE" in message
    assert "STOP_LOSS_PCT" in message
