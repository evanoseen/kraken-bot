"""Smoke tests that prove the scaffold works.

These are intentionally trivial. They exist so `pytest --collect-only` finds
at least one test and exits 0 instead of 5 (no-tests-collected). Day 10+
backlog adds real per-module test coverage.
"""
from __future__ import annotations


def test_scaffold_imports():
    """The conftest module imports cleanly."""
    from tests import conftest  # noqa: F401


def test_kraken_dryrun_fixture_returns_canned_balance(kraken_dryrun):
    """The shared fixture answers a private Balance call with the canned $100 CAD response."""
    resp = kraken_dryrun.query_private("Balance")
    assert resp["error"] == []
    assert resp["result"]["ZCAD"] == "100.00"


def test_kraken_dryrun_fixture_returns_canned_ticker(kraken_dryrun):
    """The shared fixture answers a public Ticker call with the canned XDGCAD payload."""
    resp = kraken_dryrun.query_public("Ticker", {"pair": "XDGCAD"})
    assert resp["error"] == []
    assert "XDGCAD" in resp["result"]
