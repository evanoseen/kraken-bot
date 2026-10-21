"""Day 123 contract: next_day.py picks up where the backlog actually left
off, not from a stale calendar-offset guess, and isn't fooled by the file's
own early history (Days 1-31/56-83) never having gotten Result paragraphs.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

# Load scripts/next_day.py by path (the scripts/ dir isn't a package).
_MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "next_day.py"
_spec = importlib.util.spec_from_file_location("next_day", _MODULE_PATH)
next_day = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(next_day)

_BACKLOG = Path(__file__).resolve().parent.parent / "DAILY_ITERATIONS.md"


def test_find_next_day_picks_up_after_last_result():
    text = (
        "## Day 1: first\n"
        "**Result (2026-01-01):** done.\n\n"
        "## Day 2: second\n"
        "**Result (2026-01-02):** done.\n\n"
        "## Day 3: third\n"
        "no result yet\n"
    )
    assert next_day.find_next_day(text) == 3


def test_find_next_day_advances_past_a_fully_done_backlog():
    text = (
        "## Day 1: first\n"
        "**Result (2026-01-01):** done.\n\n"
        "## Day 2: second\n"
        "**Result (2026-01-02):** done.\n"
    )
    assert next_day.find_next_day(text) == 3


def test_find_next_day_ignores_earlier_gaps_without_result():
    # Regression test for the bug this day fixed: Days 1-31 in the real
    # DAILY_ITERATIONS.md have no "**Result (" paragraph (never backfilled)
    # and Days 56-83 don't either (the convention started at Day 84) -- a
    # naive "lowest day anywhere without a Result" scan resolves to Day 1,
    # not the actual next day. The highest-numbered header must always win.
    text = (
        "## Day 1: ancient, never got a Result paragraph\n"
        "some prose, no Result marker at all\n\n"
        "## Day 56: also pre-dates the convention\n"
        "shipped, but no Result paragraph either\n\n"
        "## Day 122: most recent, done\n"
        "**Result (2026-10-20):** done.\n"
    )
    assert next_day.find_next_day(text) == 123


def test_find_next_day_uses_the_header_with_the_highest_number_even_out_of_order():
    text = (
        "## Day 5: out of order\n"
        "**Result (2026-01-05):** done.\n\n"
        "## Day 3: earlier, appears later in the file\n"
        "**Result (2026-01-03):** done.\n"
    )
    assert next_day.find_next_day(text) == 6


def test_find_next_day_raises_without_any_day_headers():
    with pytest.raises(ValueError):
        next_day.find_next_day("no day headers in here at all")


def test_find_next_day_against_the_real_backlog_file():
    # Property check, not a hardcoded day number, so this doesn't need
    # updating every time a new day gets appended: whatever day comes back
    # must be the day right after the file's current highest header, and if
    # that header already exists it must not have a Result yet.
    text = _BACKLOG.read_text(encoding="utf-8")
    headers = list(next_day._DAY_HEADER.finditer(text))
    last_day = max(int(m.group(1)) for m in headers)

    result = next_day.find_next_day(text)

    assert result in (last_day, last_day + 1)
    block_start_positions = {int(m.group(1)): m.end() for m in headers}
    if result in block_start_positions:
        start = block_start_positions[result]
        ends_after = [m.start() for m in headers if m.start() > start]
        end = min(ends_after) if ends_after else len(text)
        assert next_day._RESULT_MARKER not in text[start:end]


def test_main_prints_next_day_and_returns_0(tmp_path, capsys):
    backlog = tmp_path / "DAILY_ITERATIONS.md"
    backlog.write_text("## Day 7: x\n**Result (2026-01-01):** done.\n")

    rc = next_day.main([str(backlog)])

    assert rc == 0
    assert capsys.readouterr().out.strip() == "8"


def test_main_missing_file_returns_1(tmp_path, capsys):
    rc = next_day.main([str(tmp_path / "does_not_exist.md")])
    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_main_no_headers_returns_1(tmp_path, capsys):
    backlog = tmp_path / "DAILY_ITERATIONS.md"
    backlog.write_text("nothing here")

    rc = next_day.main([str(backlog)])

    assert rc == 1
    assert "error" in capsys.readouterr().err


def test_main_wrong_arg_count_returns_2(capsys):
    rc = next_day.main([])
    assert rc == 2
    assert "usage" in capsys.readouterr().err
