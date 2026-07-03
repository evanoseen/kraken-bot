"""Tests for Day 37 — graceful shutdown on SIGINT/SIGTERM."""
from __future__ import annotations

import signal
import pytest
import trader


@pytest.fixture(autouse=True)
def reset_globals():
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0
    yield
    trader._starting_balance = None
    trader._peak_balance = None
    trader._trades_today = 0
    trader._wins = 0
    trader._losses = 0


def _run_main_until_signal(mocker, monkeypatch, tmp_path, sig):
    monkeypatch.setenv("DRY_RUN", "true")
    monkeypatch.setenv("DAILY_LOSS_LIMIT", "9999")
    monkeypatch.setenv("MAX_DRAWDOWN_PCT", "0.99")
    monkeypatch.setenv("MAX_TRADES_PER_DAY", "100")
    monkeypatch.chdir(tmp_path)

    import main as main_mod
    mocker.patch("health.run_checks")
    mocker.patch("trader.run_trading_cycle")
    mocker.patch("heartbeat.write_heartbeat")

    call_count = 0

    def fake_sleep(_):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            import os
            os.kill(os.getpid(), sig)

    mocker.patch("main.time.sleep", side_effect=fake_sleep)
    mocker.patch("schedule.every").return_value.minutes.do.return_value = None
    mocker.patch("schedule.run_pending")

    with pytest.raises(SystemExit) as exc:
        main_mod.main([])
    return exc


def test_sigint_exits_zero(mocker, monkeypatch, tmp_path):
    exc = _run_main_until_signal(mocker, monkeypatch, tmp_path, signal.SIGINT)
    assert exc.value.code == 0


def test_sigterm_exits_zero(mocker, monkeypatch, tmp_path):
    exc = _run_main_until_signal(mocker, monkeypatch, tmp_path, signal.SIGTERM)
    assert exc.value.code == 0


def test_shutdown_logs_session_summary(mocker, monkeypatch, tmp_path, caplog):
    import logging
    trader._trades_today = 4
    trader._wins = 3
    trader._losses = 1
    trader._starting_balance = 100.0
    with caplog.at_level(logging.INFO, logger="main"):
        _run_main_until_signal(mocker, monkeypatch, tmp_path, signal.SIGINT)
    assert "4 trade" in caplog.text
    assert "3/1" in caplog.text


def test_shutdown_logs_signal_name(mocker, monkeypatch, tmp_path, caplog):
    import logging
    with caplog.at_level(logging.INFO, logger="main"):
        _run_main_until_signal(mocker, monkeypatch, tmp_path, signal.SIGINT)
    assert "SIGINT" in caplog.text
