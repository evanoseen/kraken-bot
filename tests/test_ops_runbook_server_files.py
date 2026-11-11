"""Day 144: OPS_RUNBOOK.md section 7 ("Files on the server") never once
mentioned the `KILL` file.

That section's own job, by its own words, is "a quick map so you do not
have to remember" every fixed-name runtime file that lives in
`/root/kraken-bot/` — and it does list all seven of the other fixed-name
state files the bot's modules define (`positions.json`, `seen_listings.json`,
`trades.csv`, `trades.jsonl`, `status.json`, `last_run.txt`, `bot.log`).
`KILL` (`kill_switch.py`) is the eighth, and the only one missing — despite
section 6 of this same file documenting exactly how to create it
(`touch .../KILL`), check it, and remove it, and line 438 noting it is
"git-ignored so it never ships in a deploy," the same reason `.env` (which
*is* listed) isn't in git either.

Modeled on tests/test_ops_runbook_daily_pnl.py's approach: rather than
hardcoding the eight filenames (which could itself drift the same way the
doc did), it derives each one straight from the real constant/default in
the module that owns it and asserts every one actually appears in section
7's file-tree block specifically, not just anywhere in the doc.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OPS_RUNBOOK = REPO_ROOT / "OPS_RUNBOOK.md"

# (source file, regex whose single capture group is the fixed filename)
_FILE_PATTERNS = [
    ("heartbeat.py", r'HEARTBEAT_FILE\s*=.*?"([^"]+)"'),
    ("listing_monitor.py", r'SEEN_FILE\s*=\s*"([^"]+)"'),
    ("positions.py", r'POSITIONS_FILE\s*=\s*"([^"]+)"'),
    ("positions.py", r'TRADES_JSONL\s*=\s*"([^"]+)"'),
    ("kill_switch.py", r'KILL_FILE\s*=.*?"([^"]+)"'),
    ("status.py", r'os\.getenv\("STATUS_FILE",\s*"([^"]+)"\)'),
    ("trade_logger.py", r'os\.getenv\("TRADE_LOG_PATH",\s*"([^"]+)"\)'),
]


def _server_state_filenames() -> set[str]:
    names = set()
    for relpath, pattern in _FILE_PATTERNS:
        text = (REPO_ROOT / relpath).read_text()
        match = re.search(pattern, text)
        assert match, f"couldn't find {pattern!r} in {relpath}"
        names.add(match.group(1))
    return names


def _section_7_text() -> str:
    text = OPS_RUNBOOK.read_text()
    match = re.search(r"## 7\. Files on the server\n(.*?)\n## 8\.", text, re.DOTALL)
    assert match, "OPS_RUNBOOK.md's section 7 ('Files on the server') not found"
    return match.group(1)


def test_section_7_lists_bot_log():
    # sanity check that the extraction method matches a file already known-present
    assert "bot.log" in _section_7_text()


def test_section_7_lists_every_fixed_name_state_file():
    names = _server_state_filenames()
    assert len(names) == 7, f"expected 7 distinct fixed-name state files, derived {names}"
    section = _section_7_text()
    missing = {name for name in names if name not in section}
    assert not missing, (
        f"OPS_RUNBOOK.md section 7's 'Files on the server' map is missing: {sorted(missing)} "
        "— a fixed-name runtime file the bot's own code defines was never added to the map "
        "whose entire job is listing them"
    )
