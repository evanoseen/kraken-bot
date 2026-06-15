from __future__ import annotations

from datetime import datetime, timezone

from heartbeat import read_heartbeat, write_heartbeat


def test_write_heartbeat_creates_parseable_iso_timestamp(tmp_path):
    target = tmp_path / "last_run.txt"

    stamp = write_heartbeat(target)

    assert target.exists()
    # The written value round-trips through ISO 8601 parsing.
    parsed = datetime.fromisoformat(target.read_text().strip())
    assert parsed == datetime.fromisoformat(stamp)
    assert parsed.tzinfo is not None  # UTC-aware, not naive


def test_write_heartbeat_overwrites_previous(tmp_path):
    target = tmp_path / "last_run.txt"
    target.write_text("2000-01-01T00:00:00+00:00\n")

    write_heartbeat(target)

    parsed = read_heartbeat(target)
    assert parsed is not None
    assert parsed.year > 2000


def test_read_heartbeat_missing_returns_none(tmp_path):
    assert read_heartbeat(tmp_path / "nope.txt") is None


def test_read_heartbeat_empty_returns_none(tmp_path):
    target = tmp_path / "last_run.txt"
    target.write_text("   \n")
    assert read_heartbeat(target) is None
