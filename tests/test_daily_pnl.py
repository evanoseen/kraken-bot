"""Day 23 contract: daily_pnl aggregates trades.jsonl into a per-day report.

Covers the import-safe, network-free core: loading JSONL (incl. missing/empty/
malformed files), per-day aggregation of buy/sell counts + net cash flow +
realized PnL, total realized PnL, and the assembled report text. The live
Kraken balance fetch is intentionally not exercised here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import pytest

# Load scripts/daily_pnl.py by path (the scripts/ dir isn't a package).
_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "daily_pnl.py"
_spec = importlib.util.spec_from_file_location("daily_pnl", _MODULE_PATH)
daily_pnl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(daily_pnl)


def _write_jsonl(path: Path, events: list[dict]) -> Path:
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


@pytest.fixture
def sample_trades() -> list[dict]:
    return [
        {"timestamp": "2026-06-17T10:00:00", "coin": "DOGE", "side": "buy",
         "amount_cad": 40.0, "pnl_cad": None},
        {"timestamp": "2026-06-17T14:00:00", "coin": "DOGE", "side": "sell",
         "amount_cad": 52.0, "pnl_cad": 12.0},
        {"timestamp": "2026-06-18T09:00:00", "coin": "SHIB", "side": "buy",
         "amount_cad": 30.0, "pnl_cad": None},
        {"timestamp": "2026-06-18T16:00:00", "coin": "SHIB", "side": "sell",
         "amount_cad": 25.0, "pnl_cad": -5.0},
    ]


def test_load_trades_missing_file_returns_empty(tmp_path):
    assert daily_pnl.load_trades(tmp_path / "nope.jsonl") == []


def test_load_trades_skips_blank_and_malformed_lines(tmp_path):
    p = tmp_path / "trades.jsonl"
    p.write_text('{"side": "buy", "amount_cad": 10}\n\nnot-json\n{"side": "sell", "amount_cad": 12}\n')
    trades = daily_pnl.load_trades(p)
    assert len(trades) == 2


def test_aggregate_by_day_counts_and_cash_flow(sample_trades):
    agg = daily_pnl.aggregate_by_day(sample_trades)
    assert list(agg.keys()) == ["2026-06-17", "2026-06-18"]  # sorted ascending

    d17 = agg["2026-06-17"]
    assert d17["buys"] == 1 and d17["sells"] == 1
    assert d17["net_cad"] == pytest.approx(12.0)      # +52 sell - 40 buy
    assert d17["realized_pnl"] == pytest.approx(12.0)

    d18 = agg["2026-06-18"]
    assert d18["net_cad"] == pytest.approx(-5.0)       # +25 sell - 30 buy
    assert d18["realized_pnl"] == pytest.approx(-5.0)


def test_total_realized_pnl(sample_trades):
    assert daily_pnl.total_realized_pnl(sample_trades) == pytest.approx(7.0)  # 12 - 5


def test_build_report_has_table_and_net_pnl_line(sample_trades):
    report = daily_pnl.build_report(sample_trades, balance=None)
    assert "Day" in report and "Net CAD" in report
    assert "2026-06-17" in report and "2026-06-18" in report
    assert "Net realized PnL: +7.00 CAD" in report
    assert "Current Kraken balance" not in report  # balance omitted when None


def test_build_report_includes_balance_when_provided(sample_trades):
    report = daily_pnl.build_report(sample_trades, balance=123.45)
    assert "Current Kraken balance: 123.45 CAD" in report


def test_format_table_handles_no_trades():
    assert "(no trades recorded yet)" in daily_pnl.format_table({})


def test_main_runs_offline_with_no_balance(tmp_path, sample_trades, capsys):
    p = _write_jsonl(tmp_path / "trades.jsonl", sample_trades)
    rc = daily_pnl.main(["--file", str(p), "--no-balance"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Net realized PnL: +7.00 CAD" in out
    assert "Current Kraken balance" not in out


# ── Day 60: --since/--until range filtering ─────────────────────────────────

def test_filter_by_range_since_only(sample_trades):
    filtered = daily_pnl.filter_by_range(sample_trades, since="2026-06-18", until=None)
    assert all(daily_pnl._day(t) >= "2026-06-18" for t in filtered)
    assert len(filtered) == 2


def test_filter_by_range_until_only(sample_trades):
    filtered = daily_pnl.filter_by_range(sample_trades, since=None, until="2026-06-17")
    assert all(daily_pnl._day(t) <= "2026-06-17" for t in filtered)
    assert len(filtered) == 2


def test_filter_by_range_both_bounds_inclusive(sample_trades):
    filtered = daily_pnl.filter_by_range(sample_trades, since="2026-06-17", until="2026-06-17")
    assert len(filtered) == 2
    assert all(daily_pnl._day(t) == "2026-06-17" for t in filtered)


def test_filter_by_range_no_bounds_returns_everything(sample_trades):
    assert daily_pnl.filter_by_range(sample_trades, since=None, until=None) == sample_trades


def test_filter_by_range_excludes_everything_outside_window(sample_trades):
    assert daily_pnl.filter_by_range(sample_trades, since="2026-07-01", until="2026-07-31") == []


def test_parse_date_arg_accepts_valid_date():
    assert daily_pnl._parse_date_arg("2026-06-17") == "2026-06-17"


def test_parse_date_arg_rejects_malformed_date():
    with pytest.raises(argparse.ArgumentTypeError):
        daily_pnl._parse_date_arg("06/17/2026")


def test_main_since_until_filters_report(tmp_path, sample_trades, capsys):
    p = _write_jsonl(tmp_path / "trades.jsonl", sample_trades)
    rc = daily_pnl.main(["--file", str(p), "--no-balance", "--since", "2026-06-18", "--until", "2026-06-18"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "2026-06-18" in out
    assert "2026-06-17" not in out
    assert "Net realized PnL: -5.00 CAD" in out  # only the 06-18 sell's pnl


def test_main_since_after_until_errors(tmp_path, sample_trades):
    p = _write_jsonl(tmp_path / "trades.jsonl", sample_trades)
    with pytest.raises(SystemExit):
        daily_pnl.main(["--file", str(p), "--no-balance", "--since", "2026-06-18", "--until", "2026-06-17"])
