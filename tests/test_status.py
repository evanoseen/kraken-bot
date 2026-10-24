"""Tests for Day 45 — JSON status file."""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
import pytest
import status

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"

ISC_19_ROW_PATTERN = re.compile(
    r"ISC-19 \| file \| `(\S+)` has (\d+) fields after a cycle \| (\d+) keys"
)


@pytest.fixture(autouse=True)
def tmp_status(tmp_path, monkeypatch):
    p = tmp_path / "status_test.json"
    monkeypatch.setenv("STATUS_FILE", str(p))
    return p


def test_file_created(tmp_status):
    assert not tmp_status.exists()
    status.write_status(balance=100.0, open_positions=2, trades_today=3, wins=2, losses=1)
    assert tmp_status.exists()


def test_fields_present(tmp_status):
    status.write_status(balance=100.0, open_positions=2, trades_today=3, wins=2, losses=1, starting_balance=90.0)
    data = json.loads(tmp_status.read_text())
    assert "updated_at" in data
    assert data["balance_cad"] == 100.0
    assert data["open_positions"] == 2
    assert data["trades_today"] == 3
    assert data["wins"] == 2
    assert data["losses"] == 1


def test_win_rate_calculated(tmp_status):
    status.write_status(balance=100.0, open_positions=0, trades_today=4, wins=3, losses=1)
    data = json.loads(tmp_status.read_text())
    assert data["win_rate"] == 0.75


def test_win_rate_none_when_no_trades(tmp_status):
    status.write_status(balance=100.0, open_positions=0, trades_today=0, wins=0, losses=0)
    data = json.loads(tmp_status.read_text())
    assert data["win_rate"] is None


def test_session_pnl_calculated(tmp_status):
    status.write_status(balance=115.0, open_positions=1, trades_today=2, wins=1, losses=1, starting_balance=100.0)
    data = json.loads(tmp_status.read_text())
    assert data["session_pnl_cad"] == 15.0
    assert data["starting_balance_cad"] == 100.0


def test_session_pnl_none_without_starting_balance(tmp_status):
    status.write_status(balance=100.0, open_positions=0, trades_today=0, wins=0, losses=0)
    data = json.loads(tmp_status.read_text())
    assert data["session_pnl_cad"] is None
    assert data["starting_balance_cad"] is None


def test_file_overwritten_on_second_write(tmp_status):
    status.write_status(balance=100.0, open_positions=0, trades_today=1, wins=1, losses=0)
    status.write_status(balance=110.0, open_positions=1, trades_today=3, wins=2, losses=1)
    data = json.loads(tmp_status.read_text())
    assert data["balance_cad"] == 110.0
    assert data["trades_today"] == 3


def test_fail_soft_on_bad_path(monkeypatch, caplog):
    monkeypatch.setenv("STATUS_FILE", "/nonexistent/path/status.json")
    with caplog.at_level(logging.WARNING, logger="status"):
        status.write_status(balance=100.0, open_positions=0, trades_today=0, wins=0, losses=0)
    assert "failed to write" in caplog.text


def test_isa_status_json_schema_claim_matches_reality(tmp_status):
    """Day 126: ISA.md's ISC-19 verification-table row claims a filename and
    a field count for the JSON status file. Both must match the real
    write_status() payload — this used to claim `latest_status.json` and
    5 fields (the original Day 45 shape); the filename was fixed in ISC-19's
    own checklist bullet but the table row never was, and the real payload
    has since grown to 10 keys without the table being updated either."""
    match = ISC_19_ROW_PATTERN.search(ISA.read_text())
    assert match, "Expected an ISC-19 status-file row in ISA.md's verification table"
    claimed_filename, claimed_field_count, claimed_key_count = match.groups()
    assert claimed_field_count == claimed_key_count, (
        "ISA.md's ISC-19 row states a different 'N fields' count than 'N keys' "
        f"threshold: {claimed_field_count} vs {claimed_key_count}"
    )
    assert claimed_filename == "status.json", (
        f"ISA.md's ISC-19 row claims the status file is named {claimed_filename!r}, "
        "but write_status() writes status.json by default"
    )

    status.write_status(balance=100.0, open_positions=1, trades_today=1, wins=1, losses=0)
    real_keys = set(json.loads(tmp_status.read_text()).keys())

    assert len(real_keys) == int(claimed_field_count), (
        f"ISA.md's ISC-19 row claims status.json has {claimed_field_count} fields, "
        f"but write_status() actually writes {len(real_keys)}: {sorted(real_keys)}"
    )
