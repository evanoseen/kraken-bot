from __future__ import annotations

from pathlib import Path

KILL_FILE = Path(__file__).resolve().parent / "KILL"


def kill_switch_active(path: Path = KILL_FILE) -> bool:
    """Return True if the kill-switch file exists in the repo root.

    Checked at the top of every trading cycle. `touch KILL` halts all trading
    instantly — the next cycle becomes a no-op (no network calls, no orders) —
    without needing SSH + systemctl. `rm KILL` resumes trading on the following
    cycle. No network or state mutation; a pure filesystem probe.
    """
    return path.exists()
