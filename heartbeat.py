from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

HEARTBEAT_FILE = Path(__file__).resolve().parent / "last_run.txt"


def write_heartbeat(path: Path = HEARTBEAT_FILE) -> str:
    """Write the current UTC time as an ISO 8601 timestamp to the heartbeat file.

    Called at the end of every trading cycle so "is the bot alive?" can be
    answered by reading one file instead of SSHing into the VPS. Side effect:
    overwrites `path` on disk. Returns the timestamp string written.
    """
    stamp = datetime.now(timezone.utc).isoformat()
    path.write_text(stamp + "\n")
    return stamp


def read_heartbeat(path: Path = HEARTBEAT_FILE) -> datetime | None:
    """Return the last heartbeat as a datetime, or None if missing or empty.

    No network or state mutation. Used by ops scripts to check freshness.
    """
    try:
        text = path.read_text().strip()
    except FileNotFoundError:
        return None
    if not text:
        return None
    return datetime.fromisoformat(text)
