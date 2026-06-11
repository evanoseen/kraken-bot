"""Day 20 contract: every `log_trade` call appends one valid JSON line to trades.jsonl.

Pins:
1. A single call produces a single valid JSON line — the exact one-liner
   from the Day 20 done-when probe runs against it cleanly.
2. The line contains all required fields per the backlog spec: timestamp,
   pair, side, volume, price, order_id, signal_source.
3. `action="buy_newlisting"` decomposes into `side="buy"`,
   `signal_source="newlisting"`; same for stoploss / takeprofit / signal.
4. Multiple calls produce multiple lines, all valid JSON.
5. Optional `pair` and `order_id` default to `None` (serialized as JSON null)
   when callers don't pass them — current trader.py call sites do not pass
   either, so this MUST work.
6. CSV side effect still works — backward compat.

Each test runs in a `tmp_path` cwd so writes don't pollute the repo root.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def in_tmp_cwd(tmp_path, monkeypatch):
    """Chdir into a tmp_path so every trades.jsonl/csv write lands there."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


# ─── Core contract ────────────────────────────────────────────────────────


def test_single_call_writes_one_valid_json_line(in_tmp_cwd):
    """A single log_trade call produces one parseable JSON line."""
    from positions import log_trade

    log_trade("DOGE", "buy_signal", price=0.10, amount_cad=25.0)

    jsonl_path = in_tmp_cwd / "trades.jsonl"
    assert jsonl_path.exists()

    lines = jsonl_path.read_text().splitlines()
    assert len(lines) == 1

    event = json.loads(lines[0])
    assert event["coin"] == "DOGE"
    assert event["side"] == "buy"
    assert event["signal_source"] == "signal"
    assert event["price"] == 0.10
    assert event["amount_cad"] == 25.0


def test_jsonl_contains_all_required_backlog_fields(in_tmp_cwd):
    """Every event has the 7 spec fields plus the 3 we track for richer analysis."""
    from positions import log_trade

    log_trade("PEPE", "sell_takeprofit", price=0.000015, amount_cad=50.0, pnl=12.50)

    event = json.loads((in_tmp_cwd / "trades.jsonl").read_text().splitlines()[0])

    required = {
        "timestamp", "pair", "side", "volume", "price", "order_id", "signal_source",
    }
    extras = {"coin", "amount_cad", "pnl_cad"}
    assert required.issubset(event.keys()), (
        f"missing: {required - event.keys()}"
    )
    assert extras.issubset(event.keys())


@pytest.mark.parametrize("action,side,source", [
    ("buy_newlisting", "buy", "newlisting"),
    ("buy_signal", "buy", "signal"),
    ("sell_signal", "sell", "signal"),
    ("sell_stoploss", "sell", "stoploss"),
    ("sell_takeprofit", "sell", "takeprofit"),
])
def test_action_decomposes_into_side_and_signal_source(in_tmp_cwd, action, side, source):
    """All 5 trader.py call patterns decompose to the expected side + source."""
    from positions import log_trade

    log_trade("COIN", action, price=1.0, amount_cad=10.0)

    event = json.loads((in_tmp_cwd / "trades.jsonl").read_text().splitlines()[-1])
    assert event["side"] == side
    assert event["signal_source"] == source


def test_multiple_calls_produce_multiple_lines(in_tmp_cwd):
    """Three calls -> three valid JSON lines."""
    from positions import log_trade

    log_trade("DOGE", "buy_signal", 0.10, 25.0)
    log_trade("SHIB", "buy_newlisting", 0.00001, 30.0)
    log_trade("DOGE", "sell_takeprofit", 0.13, 32.50, pnl=7.5)

    lines = (in_tmp_cwd / "trades.jsonl").read_text().splitlines()
    assert len(lines) == 3
    events = [json.loads(l) for l in lines]
    assert events[0]["coin"] == "DOGE" and events[0]["side"] == "buy"
    assert events[1]["coin"] == "SHIB" and events[1]["signal_source"] == "newlisting"
    assert events[2]["coin"] == "DOGE" and events[2]["pnl_cad"] == 7.5


def test_optional_pair_and_order_id_default_to_null(in_tmp_cwd):
    """Trader's current call sites don't pass pair/order_id; both serialize as JSON null."""
    from positions import log_trade

    log_trade("DOGE", "buy_signal", 0.10, 25.0)
    event = json.loads((in_tmp_cwd / "trades.jsonl").read_text().splitlines()[0])
    assert event["pair"] is None
    assert event["order_id"] is None


def test_pair_and_order_id_round_trip_when_passed(in_tmp_cwd):
    """Callers that DO have pair/order_id can pass them and they land in the event."""
    from positions import log_trade

    log_trade(
        "DOGE", "buy_signal", 0.10, 25.0,
        pair="DOGECAD", order_id="OABCDE-12345-FGHIJK",
    )
    event = json.loads((in_tmp_cwd / "trades.jsonl").read_text().splitlines()[0])
    assert event["pair"] == "DOGECAD"
    assert event["order_id"] == "OABCDE-12345-FGHIJK"


# ─── CSV backward compat ──────────────────────────────────────────────────


def test_csv_still_written_alongside_jsonl(in_tmp_cwd):
    """Legacy trades.csv keeps working — downstream tooling does not break."""
    from positions import log_trade

    log_trade("DOGE", "buy_signal", 0.10, 25.0)

    csv_path = in_tmp_cwd / "trades.csv"
    jsonl_path = in_tmp_cwd / "trades.jsonl"
    assert csv_path.exists()
    assert jsonl_path.exists()

    csv_lines = csv_path.read_text().splitlines()
    # Header + one data row
    assert len(csv_lines) == 2
    assert csv_lines[0] == "timestamp,coin,action,price,amount_cad,pnl_cad"


# ─── Done-when probe (verbatim) ───────────────────────────────────────────


def test_done_when_probe_runs_clean(in_tmp_cwd):
    """The exact one-liner from the Day 20 done-when probe exits 0."""
    from positions import log_trade

    log_trade("DOGE", "buy_signal", 0.10, 25.0)
    log_trade("PEPE", "sell_takeprofit", 0.00001, 50.0, pnl=8.0)

    cmd = [
        sys.executable, "-c",
        "import json; [json.loads(l) for l in open('trades.jsonl')]",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(in_tmp_cwd))
    assert result.returncode == 0, result.stderr


# ─── Gitignore covers it ──────────────────────────────────────────────────


def test_gitignore_excludes_trades_jsonl():
    """`.gitignore` lists `trades.jsonl` so committed state stays clean."""
    text = (REPO_ROOT / ".gitignore").read_text()
    assert "trades.jsonl" in text
