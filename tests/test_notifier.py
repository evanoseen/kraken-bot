"""Tests for notifier.py (Day 26 — Telegram trade alerts)."""
from __future__ import annotations

import pytest
import requests

import notifier


@pytest.fixture()
def telegram_env(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")


def test_no_op_when_token_missing(monkeypatch, mocker):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    post = mocker.patch("notifier.requests.post")
    notifier.notify_trade("buy_signal", "DOGE", 10.0, 0.05)
    post.assert_not_called()


def test_no_op_when_chat_id_missing(monkeypatch, mocker):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    post = mocker.patch("notifier.requests.post")
    notifier.notify_trade("buy_signal", "DOGE", 10.0, 0.05)
    post.assert_not_called()


def test_sends_message_on_buy(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_trade("buy_signal", "DOGE", 12.50, 0.0823, confidence=0.88)
    post.assert_called_once()
    payload = post.call_args.kwargs["json"]
    assert payload["chat_id"] == "12345"
    assert "BUY" in payload["text"]
    assert "DOGE" in payload["text"]
    assert "12.50" in payload["text"]
    assert "88%" in payload["text"]


def test_sends_stoploss_with_pnl(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_trade("sell_stoploss", "SHIB", 11.20, 0.0000082, pnl=-1.30)
    payload = post.call_args.kwargs["json"]
    assert "STOP-LOSS" in payload["text"]
    assert "-$1.30" in payload["text"]


def test_network_error_is_non_fatal(telegram_env, mocker):
    mocker.patch("notifier.requests.post", side_effect=requests.ConnectionError("offline"))
    notifier.notify_trade("buy_signal", "DOGE", 10.0, 0.05)


def test_bad_http_status_logs_warning(telegram_env, mocker, caplog):
    mock_resp = mocker.Mock()
    mock_resp.ok = False
    mock_resp.status_code = 400
    mock_resp.text = "Bad Request"
    mocker.patch("notifier.requests.post", return_value=mock_resp)
    import logging
    with caplog.at_level(logging.WARNING, logger="notifier"):
        notifier.notify_trade("sell_signal", "DOGE", 10.0, 0.05)
    assert "400" in caplog.text


def test_dry_run_prefix_in_message(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_trade("buy_signal", "DOGE", 10.0, 0.05, dry_run=True)
    payload = post.call_args.kwargs["json"]
    assert "[DRY RUN]" in payload["text"]


def test_shutdown_no_op_when_token_missing(monkeypatch, mocker):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    post = mocker.patch("notifier.requests.post")
    notifier.notify_shutdown(4, 3, 1, 100.0, "SIGINT")
    post.assert_not_called()


def test_shutdown_sends_session_summary(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_shutdown(4, 3, 1, 100.0, "SIGINT")
    payload = post.call_args.kwargs["json"]
    assert "SIGINT" in payload["text"]
    assert "Trades today: 4" in payload["text"]
    assert "3/1" in payload["text"]
    assert "100.00" in payload["text"]


def test_shutdown_omits_balance_when_none(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_shutdown(0, 0, 0, None, "SIGTERM")
    payload = post.call_args.kwargs["json"]
    assert "n/a" in payload["text"]
    assert "Started at" not in payload["text"]


def test_shutdown_network_error_is_non_fatal(telegram_env, mocker):
    mocker.patch("notifier.requests.post", side_effect=requests.ConnectionError("offline"))
    notifier.notify_shutdown(1, 1, 0, 50.0, "SIGINT")


def test_heartbeat_stale_no_op_when_token_missing(monkeypatch, mocker):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    post = mocker.patch("notifier.requests.post")
    notifier.notify_heartbeat_stale(45.0, 30.0)
    post.assert_not_called()


def test_heartbeat_stale_sends_age_and_threshold(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_heartbeat_stale(45.3, 30.0)
    payload = post.call_args.kwargs["json"]
    assert "STALE" in payload["text"]
    assert "45.3m" in payload["text"]
    assert "30m" in payload["text"]


def test_heartbeat_missing_sends_missing_message(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_heartbeat_stale(None, 30.0)
    payload = post.call_args.kwargs["json"]
    assert "MISSING" in payload["text"]


def test_heartbeat_stale_network_error_is_non_fatal(telegram_env, mocker):
    mocker.patch("notifier.requests.post", side_effect=requests.ConnectionError("offline"))
    notifier.notify_heartbeat_stale(60.0, 30.0)


def test_reconciliation_no_op_when_token_missing(monkeypatch, mocker):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    post = mocker.patch("notifier.requests.post")
    notifier.notify_reconciliation_mismatch(["DOGE"], [])
    post.assert_not_called()


def test_reconciliation_reports_only_in_kraken(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_reconciliation_mismatch(["DOGE", "SHIB"], [])
    payload = post.call_args.kwargs["json"]
    assert "Held on Kraken, not tracked: DOGE, SHIB" in payload["text"]
    assert "Tracked, not held on Kraken" not in payload["text"]


def test_reconciliation_reports_only_in_positions(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_reconciliation_mismatch([], ["PEPE"])
    payload = post.call_args.kwargs["json"]
    assert "Tracked, not held on Kraken: PEPE" in payload["text"]
    assert "Held on Kraken, not tracked" not in payload["text"]


def test_reconciliation_reports_both_directions(telegram_env, mocker):
    mock_resp = mocker.Mock()
    mock_resp.ok = True
    post = mocker.patch("notifier.requests.post", return_value=mock_resp)
    notifier.notify_reconciliation_mismatch(["DOGE"], ["PEPE"])
    payload = post.call_args.kwargs["json"]
    assert "Held on Kraken, not tracked: DOGE" in payload["text"]
    assert "Tracked, not held on Kraken: PEPE" in payload["text"]


def test_reconciliation_network_error_is_non_fatal(telegram_env, mocker):
    mocker.patch("notifier.requests.post", side_effect=requests.ConnectionError("offline"))
    notifier.notify_reconciliation_mismatch(["DOGE"], [])
