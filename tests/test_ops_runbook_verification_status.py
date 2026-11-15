"""Day 148: OPS_RUNBOOK.md section 9 ("Verification after any change") never
once read `status.json`.

Section 7's own "Files on the server" map describes `status.json` as the
Day 26/45 file designed to be "polled instead of SSH" — a quick machine
-readable snapshot (balance, session PnL, win rate) instead of grepping
logs by hand. But nothing in the codebase ever actually serves it over
anything but the filesystem it's written to (`trader.py`'s one
`write_status()` call), so the *only* way an operator can actually read it
is the same SSH session every other command in this runbook already uses
— and section 9, the one section whose entire job is "run this after a
deploy, rollback, env edit, or restart" to confirm the change worked, never
included it. The three things it did check (service, logs, positions,
trades) all answer "is it running," not "did the numbers come out right,"
which is exactly what `status.json` is for.

Modeled on tests/test_ops_runbook_server_files.py's approach: derives the
real default filename from `status.py` rather than hardcoding it, and
asserts it appears specifically inside section 9's verification block.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS_RUNBOOK = REPO_ROOT / "OPS_RUNBOOK.md"


def _status_filename() -> str:
    text = (REPO_ROOT / "status.py").read_text()
    match = re.search(r'os\.getenv\("STATUS_FILE",\s*"([^"]+)"\)', text)
    assert match, "couldn't find STATUS_FILE's default in status.py"
    return match.group(1)


def _section_9_text() -> str:
    text = OPS_RUNBOOK.read_text()
    match = re.search(
        r"## 9\. Verification after any change\n(.*?)\n## 10\.", text, re.DOTALL
    )
    assert match, "OPS_RUNBOOK.md's section 9 ('Verification after any change') not found"
    return match.group(1)


def test_section_9_still_checks_service_and_positions():
    # sanity check that the extraction method matches commands already known-present
    section = _section_9_text()
    assert "systemctl is-active kraken-bot" in section
    assert "positions.json" in section


def test_section_9_reads_the_status_snapshot():
    filename = _status_filename()
    section = _section_9_text()
    assert filename in section, (
        f"OPS_RUNBOOK.md section 9's verification trio never reads {filename!r} — "
        "the one file designed to answer 'did this change work' without parsing logs"
    )
