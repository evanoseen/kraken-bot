"""Tests for Day 30 — startup health check."""
from __future__ import annotations

import logging
import sys
import pytest
import health


def _make_cfg(mocker, **overrides):
    defaults = dict(
        kraken_api_key="key",
        kraken_private_key="secret",
        anthropic_api_key="anth",
        telegram_bot_token=None,
        telegram_chat_id=None,
        max_trade_amount=25.0,
        min_confidence=0.80,
        daily_loss_limit=50.0,
        max_drawdown_pct=0.20,
        max_open_positions=3,
        trade_cooldown_minutes=60.0,
        stop_loss_pct=0.10,
        take_profit_pct=0.25,
        run_interval_minutes=15,
        dry_run=True,
    )
    defaults.update(overrides)
    cfg = mocker.Mock(**defaults)
    for k, v in defaults.items():
        setattr(cfg, k, v)
    return cfg


def test_exits_on_missing_kraken_key(mocker):
    cfg = _make_cfg(mocker, kraken_api_key=None)
    mocker.patch("health._check_kraken_connectivity", return_value=True)
    with pytest.raises(SystemExit) as exc:
        health.run_checks(cfg)
    assert exc.value.code == 1


def test_exits_on_missing_anthropic_key(mocker):
    cfg = _make_cfg(mocker, anthropic_api_key=None)
    mocker.patch("health._check_kraken_connectivity", return_value=True)
    with pytest.raises(SystemExit):
        health.run_checks(cfg)


def test_passes_with_all_vars_set(mocker):
    cfg = _make_cfg(mocker)
    mocker.patch("health._check_kraken_connectivity", return_value=True)
    health.run_checks(cfg)


def test_connectivity_failure_logs_warning_but_continues(mocker, caplog):
    cfg = _make_cfg(mocker)
    mocker.patch("health._check_kraken_connectivity", return_value=False)
    with caplog.at_level(logging.WARNING, logger="health"):
        health.run_checks(cfg)
    assert "ping failed" in caplog.text.lower()


def test_banner_includes_key_config(mocker, caplog):
    cfg = _make_cfg(mocker)
    mocker.patch("health._check_kraken_connectivity", return_value=True)
    with caplog.at_level(logging.INFO, logger="health"):
        health.run_checks(cfg)
    combined = caplog.text
    assert "READY" in combined
    assert "25.00" in combined
    assert "DRY RUN" in combined


def test_banner_shows_telegram_on_when_token_set(mocker, caplog):
    cfg = _make_cfg(mocker, telegram_bot_token="tok123")
    mocker.patch("health._check_kraken_connectivity", return_value=True)
    with caplog.at_level(logging.INFO, logger="health"):
        health.run_checks(cfg)
    assert "telegram" in caplog.text.lower()
    assert "on" in caplog.text
