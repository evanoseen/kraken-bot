"""Day 59 contract: archive_trades splits old trades.csv/trades.jsonl entries
into a dated archive, keeping the live files small and valid.
"""
from __future__ import annotations

import csv
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

# Load scripts/archive_trades.py by path (the scripts/ dir isn't a package).
_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "archive_trades.py"
_spec = importlib.util.spec_from_file_location("archive_trades", _MODULE_PATH)
archive_trades = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(archive_trades)


NOW = datetime(2026, 8, 5, tzinfo=timezone.utc)
OLD = (NOW - timedelta(days=120)).isoformat()
RECENT = (NOW - timedelta(days=1)).isoformat()


def _write_csv(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "coin", "action", "price", "amount_cad", "pnl_cad"])
        writer.writerows(rows)
    return path


def _write_jsonl(path: Path, events: list[dict]) -> Path:
    path.write_text("".join(json.dumps(e) + "\n" for e in events))
    return path


@pytest.fixture
def cutoff():
    return NOW - timedelta(days=90)


def test_archive_csv_splits_old_from_recent(tmp_path, cutoff):
    src = _write_csv(tmp_path / "trades.csv", [
        [OLD, "DOGE", "buy_signal", "0.10000000", "10.00", ""],
        [RECENT, "SHIB", "sell_takeprofit", "0.00001", "12.00", "2.00"],
    ])
    archive = tmp_path / "archive.csv"

    archived, kept = archive_trades.archive_csv(src, cutoff, archive, dry_run=False)

    assert archived == 1
    assert kept == 1
    with src.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["timestamp", "coin", "action", "price", "amount_cad", "pnl_cad"]
    assert len(rows) == 2  # header + the recent row only
    assert rows[1][1] == "SHIB"

    with archive.open() as f:
        arch_rows = list(csv.reader(f))
    assert arch_rows[0] == ["timestamp", "coin", "action", "price", "amount_cad", "pnl_cad"]
    assert len(arch_rows) == 2  # header + the old row
    assert arch_rows[1][1] == "DOGE"


def test_archive_csv_dry_run_writes_nothing(tmp_path, cutoff):
    src = _write_csv(tmp_path / "trades.csv", [[OLD, "DOGE", "buy_signal", "0.1", "10.00", ""]])
    original = src.read_text()
    archive = tmp_path / "archive.csv"

    archived, kept = archive_trades.archive_csv(src, cutoff, archive, dry_run=True)

    assert archived == 1
    assert kept == 0
    assert src.read_text() == original
    assert not archive.exists()


def test_archive_csv_missing_file_is_a_noop(tmp_path, cutoff):
    archived, kept = archive_trades.archive_csv(tmp_path / "nope.csv", cutoff, tmp_path / "arc.csv", dry_run=False)
    assert (archived, kept) == (0, 0)


def test_archive_csv_no_old_rows_leaves_file_untouched(tmp_path, cutoff):
    src = _write_csv(tmp_path / "trades.csv", [[RECENT, "DOGE", "buy_signal", "0.1", "10.00", ""]])
    archive = tmp_path / "archive.csv"

    archived, kept = archive_trades.archive_csv(src, cutoff, archive, dry_run=False)

    assert (archived, kept) == (0, 1)
    assert not archive.exists()


def test_archive_jsonl_splits_old_from_recent(tmp_path, cutoff):
    src = _write_jsonl(tmp_path / "trades.jsonl", [
        {"timestamp": OLD, "coin": "DOGE", "side": "buy"},
        {"timestamp": RECENT, "coin": "SHIB", "side": "sell"},
    ])
    archive = tmp_path / "archive.jsonl"

    archived, kept = archive_trades.archive_jsonl(src, cutoff, archive, dry_run=False)

    assert (archived, kept) == (1, 1)
    kept_events = [json.loads(l) for l in src.read_text().splitlines()]
    assert kept_events == [{"timestamp": RECENT, "coin": "SHIB", "side": "sell"}]
    archived_events = [json.loads(l) for l in archive.read_text().splitlines()]
    assert archived_events == [{"timestamp": OLD, "coin": "DOGE", "side": "buy"}]


def test_archive_jsonl_keeps_malformed_lines_in_live_file(tmp_path, cutoff):
    src = tmp_path / "trades.jsonl"
    src.write_text(f'{{"timestamp": "{OLD}", "coin": "DOGE"}}\nnot-json\n\n')
    archive = tmp_path / "archive.jsonl"

    archived, kept = archive_trades.archive_jsonl(src, cutoff, archive, dry_run=False)

    assert archived == 1
    assert kept == 1
    assert "not-json" in src.read_text()


def test_archive_jsonl_dry_run_writes_nothing(tmp_path, cutoff):
    src = _write_jsonl(tmp_path / "trades.jsonl", [{"timestamp": OLD, "coin": "DOGE"}])
    original = src.read_text()
    archive = tmp_path / "archive.jsonl"

    archive_trades.archive_jsonl(src, cutoff, archive, dry_run=True)

    assert src.read_text() == original
    assert not archive.exists()


def test_main_end_to_end_splits_both_files(tmp_path, capsys):
    csv_path = _write_csv(tmp_path / "trades.csv", [
        [OLD, "DOGE", "buy_signal", "0.1", "10.00", ""],
        [RECENT, "SHIB", "sell_takeprofit", "0.00001", "12.00", "2.00"],
    ])
    jsonl_path = _write_jsonl(tmp_path / "trades.jsonl", [
        {"timestamp": OLD, "coin": "DOGE"},
        {"timestamp": RECENT, "coin": "SHIB"},
    ])

    rc = archive_trades.main(["--csv", str(csv_path), "--jsonl", str(jsonl_path), "--days", "90"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "trades.csv:   1 archived, 1 kept" in out
    assert "trades.jsonl: 1 archived, 1 kept" in out

    # Both live files remain valid, parseable, and hold only the recent entry.
    with csv_path.open() as f:
        rows = list(csv.reader(f))
    assert len(rows) == 2 and rows[1][1] == "SHIB"

    jsonl_events = [json.loads(l) for l in jsonl_path.read_text().splitlines()]
    assert jsonl_events == [{"timestamp": RECENT, "coin": "SHIB"}]


def test_main_dry_run_reports_without_writing(tmp_path, capsys):
    csv_path = _write_csv(tmp_path / "trades.csv", [[OLD, "DOGE", "buy_signal", "0.1", "10.00", ""]])
    original = csv_path.read_text()

    rc = archive_trades.main(["--csv", str(csv_path), "--jsonl", str(tmp_path / "missing.jsonl"), "--dry-run"])
    out = capsys.readouterr().out

    assert rc == 0
    assert "[DRY RUN]" in out
    assert csv_path.read_text() == original
