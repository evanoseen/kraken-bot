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
