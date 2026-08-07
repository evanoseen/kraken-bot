"""Day 61 contract: check_heartbeat alerts via Telegram when last_run.txt
is stale or missing, and stays silent when it's fresh.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Load scripts/check_heartbeat.py by path (the scripts/ dir isn't a package).
_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "check_heartbeat.py"
_spec = importlib.util.spec_from_file_location("check_heartbeat", _MODULE_PATH)
check_heartbeat = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check_heartbeat)

NOW = datetime(2026, 8, 7, 12, 0, 0, tzinfo=timezone.utc)


def test_parse_timestamp_naive_is_treated_as_utc():
    ts = check_heartbeat._parse_timestamp("2026-08-07T11:00:00")
    assert ts.tzinfo is not None
    assert ts.utcoffset().total_seconds() == 0


def test_parse_timestamp_blank_returns_none():
    assert check_heartbeat._parse_timestamp("   ") is None


def test_parse_timestamp_malformed_returns_none():
    assert check_heartbeat._parse_timestamp("not-a-timestamp") is None


def test_read_timestamp_from_missing_file_returns_none(tmp_path):
    assert check_heartbeat.read_timestamp_from_file(tmp_path / "nope.txt") is None


def test_check_fresh_heartbeat_is_not_stale():
    fresh = NOW - timedelta(minutes=5)
    is_stale, age = check_heartbeat.check(fresh, threshold_minutes=30, now=NOW)
    assert is_stale is False
    assert age == pytest.approx(5.0)


def test_check_stale_heartbeat_is_stale():
    stale = NOW - timedelta(minutes=45)
    is_stale, age = check_heartbeat.check(stale, threshold_minutes=30, now=NOW)
    assert is_stale is True
    assert age == pytest.approx(45.0)


def test_check_missing_heartbeat_is_stale_with_no_age():
    is_stale, age = check_heartbeat.check(None, threshold_minutes=30, now=NOW)
    assert is_stale is True
    assert age is None


def test_check_exactly_at_threshold_is_not_stale():
    boundary = NOW - timedelta(minutes=30)
    is_stale, _ = check_heartbeat.check(boundary, threshold_minutes=30, now=NOW)
    assert is_stale is False


# ── main(): the actual done-when — stale triggers a Telegram call, fresh doesn't ──

def test_main_fresh_heartbeat_does_not_alert(tmp_path, mocker):
    hb_file = tmp_path / "last_run.txt"
    hb_file.write_text((NOW - timedelta(minutes=5)).isoformat())
    alert = mocker.patch("notifier.notify_heartbeat_stale")

    rc = check_heartbeat.main(["--file", str(hb_file), "--threshold-minutes", "30"])
    alert.assert_not_called()
    assert rc == 0


def test_main_stale_heartbeat_triggers_telegram_call(tmp_path, mocker):
    # Timestamp far enough in the past relative to real "now" that it reads
    # as stale regardless of when the test suite actually runs.
    old = datetime.now(timezone.utc) - timedelta(days=1)
    hb_file = tmp_path / "last_run.txt"
    hb_file.write_text(old.isoformat())
    alert = mocker.patch("notifier.notify_heartbeat_stale")

    rc = check_heartbeat.main(["--file", str(hb_file), "--threshold-minutes", "30"])

    alert.assert_called_once()
    age_arg, threshold_arg = alert.call_args.args
    assert age_arg > 30
    assert threshold_arg == 30
    assert rc == 1


def test_main_missing_file_triggers_telegram_call_with_none_age(tmp_path, mocker):
    alert = mocker.patch("notifier.notify_heartbeat_stale")

    rc = check_heartbeat.main(["--file", str(tmp_path / "nope.txt"), "--threshold-minutes", "30"])

    alert.assert_called_once_with(None, 30)
    assert rc == 1


def test_main_timestamp_flag_bypasses_file(mocker):
    fresh = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    alert = mocker.patch("notifier.notify_heartbeat_stale")

    rc = check_heartbeat.main(["--timestamp", fresh, "--threshold-minutes", "30"])

    alert.assert_not_called()
    assert rc == 0


def test_default_threshold_is_2x_run_interval(monkeypatch):
    monkeypatch.setenv("RUN_INTERVAL_MINUTES", "15")
    import importlib
    import config
    importlib.reload(config)
    assert check_heartbeat._default_threshold_minutes() == 30
