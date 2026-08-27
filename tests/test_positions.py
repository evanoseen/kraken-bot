"""Tests for positions.py (Day 78).

positions.py had zero direct unit tests — every call site elsewhere mocks
record_buy/remove_position/get_position/log_trade directly rather than
exercising the real read/write/exception-handling logic. These sandbox
POSITIONS_FILE/TRADES_CSV/TRADES_JSONL into tmp_path (via
monkeypatch.chdir) and do real file round-trips.
"""
from __future__ import annotations

import json

import pytest
import positions


@pytest.fixture(autouse=True)
def sandbox(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


# ── load_positions ────────────────────────────────────────────────────────

def test_load_positions_missing_file_returns_empty_dict():
    assert positions.load_positions() == {}


def test_load_positions_malformed_json_returns_empty_dict():
    with open(positions.POSITIONS_FILE, "w") as f:
        f.write("{not valid json")
    assert positions.load_positions() == {}


def test_load_positions_reads_back_saved_data():
    positions.save_positions({"DOGE": {"entry_price": 0.1, "amount_cad": 10.0}})
    assert positions.load_positions() == {"DOGE": {"entry_price": 0.1, "amount_cad": 10.0}}


# ── save_positions ───────────────────────────────────────────────────────

def test_save_positions_writes_valid_json():
    positions.save_positions({"SHIB": {"entry_price": 0.00001, "amount_cad": 5.0}})
    with open(positions.POSITIONS_FILE) as f:
        data = json.load(f)
    assert data == {"SHIB": {"entry_price": 0.00001, "amount_cad": 5.0}}


def test_save_positions_write_failure_logs_error_not_raises(mocker, caplog):
    import logging
    mocker.patch("positions.open", side_effect=OSError("disk full"))
    with caplog.at_level(logging.ERROR, logger="positions"):
        positions.save_positions({"DOGE": {}})  # should not raise
    assert "Failed to save positions" in caplog.text


# ── record_buy ───────────────────────────────────────────────────────────

def test_record_buy_persists_entry_price_and_amount():
    positions.record_buy("DOGE", 0.08, 12.50)
    saved = positions.load_positions()
    assert saved["DOGE"]["entry_price"] == 0.08
    assert saved["DOGE"]["amount_cad"] == 12.50
    assert "timestamp" in saved["DOGE"]


def test_record_buy_preserves_existing_other_positions():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.record_buy("SHIB", 0.00001, 5.0)
    saved = positions.load_positions()
    assert set(saved.keys()) == {"DOGE", "SHIB"}


def test_record_buy_overwrites_existing_entry_for_same_coin():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.record_buy("DOGE", 0.09, 20.0)
    saved = positions.load_positions()
    assert len(saved) == 1
    assert saved["DOGE"]["entry_price"] == 0.09
    assert saved["DOGE"]["amount_cad"] == 20.0


# ── remove_position ──────────────────────────────────────────────────────

def test_remove_position_deletes_the_coin():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.remove_position("DOGE")
    assert positions.load_positions() == {}


def test_remove_position_leaves_other_coins_untouched():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.record_buy("SHIB", 0.00001, 5.0)
    positions.remove_position("DOGE")
    saved = positions.load_positions()
    assert set(saved.keys()) == {"SHIB"}


def test_remove_position_on_absent_coin_is_a_noop():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.remove_position("PEPE")  # never existed
    saved = positions.load_positions()
    assert set(saved.keys()) == {"DOGE"}


# ── update_peak_price (Day 69) ───────────────────────────────────────────

def test_update_peak_price_sets_the_field():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.update_peak_price("DOGE", 0.10)
    saved = positions.load_positions()
    assert saved["DOGE"]["peak_price"] == 0.10


def test_update_peak_price_on_absent_coin_is_a_noop():
    positions.update_peak_price("PEPE", 1.0)  # never existed
    assert positions.load_positions() == {}


def test_update_peak_price_preserves_other_fields():
    positions.record_buy("DOGE", 0.08, 12.50)
    positions.update_peak_price("DOGE", 0.10)
    saved = positions.load_positions()
    assert saved["DOGE"]["entry_price"] == 0.08
    assert saved["DOGE"]["amount_cad"] == 12.50


# ── get_position ─────────────────────────────────────────────────────────

def test_get_position_returns_the_coin_dict():
    positions.record_buy("DOGE", 0.08, 12.50)
    pos = positions.get_position("DOGE")
    assert pos["entry_price"] == 0.08


def test_get_position_returns_none_for_absent_coin():
    assert positions.get_position("NOPE") is None


# ── log_trade: CSV ───────────────────────────────────────────────────────

def test_log_trade_writes_csv_header_on_first_write():
    positions.log_trade("DOGE", "buy_signal", 0.08, 12.50)
    with open(positions.TRADES_CSV) as f:
        lines = f.readlines()
    assert lines[0].strip() == "timestamp,coin,action,price,amount_cad,pnl_cad"
    assert "DOGE,buy_signal,0.08000000,12.50," in lines[1]


def test_log_trade_does_not_rewrite_header_on_subsequent_writes():
    positions.log_trade("DOGE", "buy_signal", 0.08, 12.50)
    positions.log_trade("SHIB", "sell_stoploss", 0.00001, 5.0, pnl=-1.0)
    with open(positions.TRADES_CSV) as f:
        lines = f.readlines()
    assert len(lines) == 3  # header + 2 trades
    assert lines.count("timestamp,coin,action,price,amount_cad,pnl_cad\n") == 1


def test_log_trade_csv_includes_pnl_when_provided():
    positions.log_trade("SHIB", "sell_takeprofit", 0.00002, 8.0, pnl=3.0)
    with open(positions.TRADES_CSV) as f:
        lines = f.readlines()
    assert ",3.00" in lines[1]


def test_log_trade_csv_write_failure_logs_error_not_raises(mocker, caplog):
    import logging
    mocker.patch("positions.open", side_effect=OSError("disk full"))
    with caplog.at_level(logging.ERROR, logger="positions"):
        positions.log_trade("DOGE", "buy_signal", 0.08, 12.50)  # should not raise
    assert "Failed to log trade CSV" in caplog.text
    assert "Failed to log trade JSONL" in caplog.text


# ── log_trade: JSONL ─────────────────────────────────────────────────────

def test_log_trade_jsonl_decomposes_action_into_side_and_signal_source():
    positions.log_trade("DOGE", "sell_stoploss", 0.08, 12.50, pnl=-2.0)
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["side"] == "sell"
    assert event["signal_source"] == "stoploss"
    assert event["coin"] == "DOGE"
    assert event["pnl_cad"] == -2.0


def test_log_trade_action_without_underscore_falls_back_to_unknown():
    """side, signal_source = action, "unknown" — the else branch."""
    positions.log_trade("DOGE", "hold", 0.08, 12.50)
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["side"] == "hold"
    assert event["signal_source"] == "unknown"


def test_log_trade_jsonl_computes_volume_from_amount_and_price():
    positions.log_trade("DOGE", "buy_signal", 0.10, 10.0)
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["volume"] == pytest.approx(100.0)  # 10.0 / 0.10


def test_log_trade_jsonl_volume_is_zero_when_price_is_zero():
    positions.log_trade("DOGE", "buy_signal", 0.0, 10.0)
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["volume"] == 0.0


def test_log_trade_jsonl_passes_through_pair_and_order_id():
    positions.log_trade("DOGE", "buy_signal", 0.08, 12.50, pair="XDGCAD", order_id="ABC123")
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["pair"] == "XDGCAD"
    assert event["order_id"] == "ABC123"


def test_log_trade_jsonl_defaults_pair_and_order_id_to_none():
    positions.log_trade("DOGE", "buy_signal", 0.08, 12.50)
    with open(positions.TRADES_JSONL) as f:
        event = json.loads(f.readline())
    assert event["pair"] is None
    assert event["order_id"] is None


def test_log_trade_appends_multiple_events_to_jsonl():
    positions.log_trade("DOGE", "buy_signal", 0.08, 12.50)
    positions.log_trade("SHIB", "sell_stoploss", 0.00001, 5.0, pnl=-1.0)
    with open(positions.TRADES_JSONL) as f:
        lines = f.readlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["coin"] == "DOGE"
    assert json.loads(lines[1])["coin"] == "SHIB"
