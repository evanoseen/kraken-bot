"""Day 74 contract: reconcile_positions compares positions.json against
live Kraken holdings and reports drift in both directions.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

# Load scripts/reconcile_positions.py by path (the scripts/ dir isn't a package).
_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "reconcile_positions.py"
_spec = importlib.util.spec_from_file_location("reconcile_positions", _MODULE_PATH)
reconcile_positions = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reconcile_positions)


# ── reconcile(): pure function, no mocking needed ────────────────────────────

def test_reconcile_agrees_when_identical():
    only_kraken, only_positions = reconcile_positions.reconcile(
        {"DOGE": 100.0, "SHIB": 5000.0}, {"DOGE": {}, "SHIB": {}},
    )
    assert only_kraken == []
    assert only_positions == []


def test_reconcile_finds_coin_only_in_kraken():
    only_kraken, only_positions = reconcile_positions.reconcile(
        {"DOGE": 100.0, "PEPE": 10.0}, {"DOGE": {}},
    )
    assert only_kraken == ["PEPE"]
    assert only_positions == []


def test_reconcile_finds_coin_only_in_positions():
    only_kraken, only_positions = reconcile_positions.reconcile(
        {"DOGE": 100.0}, {"DOGE": {}, "SHIB": {}},
    )
    assert only_kraken == []
    assert only_positions == ["SHIB"]


def test_reconcile_finds_both_directions():
    """The literal Day 74 done-when."""
    only_kraken, only_positions = reconcile_positions.reconcile(
        {"DOGE": 100.0, "PEPE": 10.0}, {"DOGE": {}, "SHIB": {}},
    )
    assert only_kraken == ["PEPE"]
    assert only_positions == ["SHIB"]


def test_reconcile_results_are_sorted():
    only_kraken, only_positions = reconcile_positions.reconcile(
        {"ZCOIN": 1.0, "ACOIN": 1.0}, {"YPOS": {}, "BPOS": {}},
    )
    assert only_kraken == ["ACOIN", "ZCOIN"]
    assert only_positions == ["BPOS", "YPOS"]


# ── main(): full CLI wiring ───────────────────────────────────────────────

def test_main_reports_clean_when_in_sync(mocker, capsys):
    mocker.patch.object(reconcile_positions, "get_client", return_value=mocker.Mock())
    mocker.patch.object(reconcile_positions, "get_holdings", return_value={"DOGE": 100.0})
    mocker.patch.object(reconcile_positions, "load_positions", return_value={"DOGE": {}})
    alert = mocker.patch.object(reconcile_positions.notifier, "notify_reconciliation_mismatch")

    rc = reconcile_positions.main([])
    out = capsys.readouterr().out

    assert rc == 0
    assert "reconcile OK" in out
    alert.assert_not_called()


def test_main_reports_mismatch_both_directions(mocker, capsys):
    mocker.patch.object(reconcile_positions, "get_client", return_value=mocker.Mock())
    mocker.patch.object(reconcile_positions, "get_holdings", return_value={"DOGE": 100.0, "PEPE": 10.0})
    mocker.patch.object(reconcile_positions, "load_positions", return_value={"DOGE": {}, "SHIB": {}})
    alert = mocker.patch.object(reconcile_positions.notifier, "notify_reconciliation_mismatch")

    rc = reconcile_positions.main([])

    assert rc == 1
    alert.assert_called_once_with(["PEPE"], ["SHIB"])


def test_main_no_alert_flag_skips_telegram(mocker):
    mocker.patch.object(reconcile_positions, "get_client", return_value=mocker.Mock())
    mocker.patch.object(reconcile_positions, "get_holdings", return_value={"PEPE": 10.0})
    mocker.patch.object(reconcile_positions, "load_positions", return_value={})
    alert = mocker.patch.object(reconcile_positions.notifier, "notify_reconciliation_mismatch")

    rc = reconcile_positions.main(["--no-alert"])

    assert rc == 1
    alert.assert_not_called()
