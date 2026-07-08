"""Tests for Day 42 — CSV trade log."""
from __future__ import annotations

import csv
from pathlib import Path
import pytest
import trade_logger


@pytest.fixture(autouse=True)
def tmp_log(tmp_path, monkeypatch):
    log_file = tmp_path / "trades_test.csv"
    monkeypatch.setenv("TRADE_LOG_PATH", str(log_file))
    return log_file


def test_file_created_on_first_write(tmp_log):
    assert not tmp_log.exists()
    trade_logger.append_trade("DOGE", "buy", 12.50, 0.0823, confidence=0.88)
    assert tmp_log.exists()


def test_header_written_on_first_write(tmp_log):
    trade_logger.append_trade("DOGE", "buy", 12.50, 0.0823)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[0] == trade_logger._HEADERS


def test_trade_row_appended(tmp_log):
    trade_logger.append_trade("DOGE", "buy", 12.50, 0.0823, confidence=0.88)
    rows = list(csv.reader(tmp_log.open()))
    assert len(rows) == 2  # header + 1 trade
    row = rows[1]
    assert row[1] == "DOGE"
    assert row[2] == "buy"
    assert row[3] == "12.5000"
    assert row[5] == "0.8800"


def test_pnl_written_when_provided(tmp_log):
    trade_logger.append_trade("DOGE", "sell_stoploss", 11.20, 0.0741, pnl=-1.30)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[1][6] == "-1.3000"


def test_pnl_empty_when_not_provided(tmp_log):
    trade_logger.append_trade("BTC", "buy", 50.0, 95000.0)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[1][6] == ""


def test_confidence_empty_when_not_provided(tmp_log):
    trade_logger.append_trade("BTC", "sell_stale", 48.0, 94000.0, pnl=-2.0)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[1][5] == ""


def test_multiple_trades_no_duplicate_header(tmp_log):
    trade_logger.append_trade("DOGE", "buy", 10.0, 0.08)
    trade_logger.append_trade("SHIB", "buy", 15.0, 0.00002)
    trade_logger.append_trade("DOGE", "sell_signal", 10.5, 0.084, pnl=0.50)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[0] == trade_logger._HEADERS
    assert len(rows) == 4  # header + 3 trades


def test_coin_uppercased(tmp_log):
    trade_logger.append_trade("doge", "buy", 10.0, 0.08)
    rows = list(csv.reader(tmp_log.open()))
    assert rows[1][1] == "DOGE"


def test_fail_soft_on_bad_path(monkeypatch, caplog):
    import logging
    monkeypatch.setenv("TRADE_LOG_PATH", "/nonexistent/path/trades.csv")
    with caplog.at_level(logging.WARNING, logger="trade_logger"):
        trade_logger.append_trade("DOGE", "buy", 10.0, 0.08)
    assert "failed to write" in caplog.text
