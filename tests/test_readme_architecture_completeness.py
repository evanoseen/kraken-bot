"""Day 140: README.md's Architecture section never mentioned `health.py` or
`heartbeat.py`.

The "## Architecture" section (diagram + prose) describes the single
trading decision loop in detail — every signal source, `trader.py`,
`kraken_client.py`, `notifier.py` — but says nothing about the bot's other
real, shipped subsystem: `health.py`'s startup connectivity checks and
`heartbeat.py`'s per-cycle liveness write, plus the independent off-VPS
`scripts/check_heartbeat.py` process that polls that liveness file and
fires its own Telegram alert, entirely separate from `trader.py`'s own
trade/shutdown notifications. The data these two modules produce
(`last_run.txt`, `status.json`) is already drawn in the diagram's `POS`
node, but the modules and the second process that actually writes/reads
them never appear — the same "what's missing" failure mode as
Days 138/139, one level up the doc stack.

Modeled on tests/test_requirements_split.py's and Day 139's AST-over-
hardcoded-list approach: rather than hardcoding which modules "should" be
in the Architecture section, it derives the real local-module imports
straight from `main.py`'s own top-level `import` statements, so a future
module main.py starts depending on (and stops being purely internal
plumbing) fails this test instead of silently drifting the diagram the
way `health.py`/`heartbeat.py` already had.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
README = REPO_ROOT / "README.md"
MAIN = REPO_ROOT / "main.py"


def _architecture_section() -> str:
    text = README.read_text()
    match = re.search(r"^## Architecture\n(.*?)(?=\n## )", text, re.DOTALL | re.MULTILINE)
    assert match, "README.md must have an '## Architecture' section"
    return match.group(1)


def _main_py_local_module_imports() -> list[str]:
    """Every `import X` (not `from X import ...`) in main.py where `X.py`
    is one of this project's own top-level modules, not a third-party
    package like `schedule`."""
    tree = ast.parse(MAIN.read_text())
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if (REPO_ROOT / f"{alias.name}.py").exists():
                    names.append(alias.name)
    return names


def test_architecture_section_mentions_every_main_py_local_module():
    local_imports = _main_py_local_module_imports()
    assert local_imports, "expected main.py to import at least one local module"

    section = _architecture_section()
    missing = [name for name in local_imports if f"{name}.py" not in section]
    assert not missing, (
        f"README.md's Architecture section never mentions: {[n + '.py' for n in missing]} "
        "— main.py depends on them directly, so the diagram/prose describing the bot's "
        "architecture should too"
    )


def test_architecture_section_mentions_check_heartbeat_script():
    """`check_heartbeat.py` isn't importable from main.py (it's a standalone
    script run off-VPS, per its own docstring) so it can't be derived the
    way the test above derives health.py/heartbeat.py — but it's a second,
    independent process with its own Telegram alert path, and belongs in
    the architecture picture too."""
    section = _architecture_section()
    assert "check_heartbeat.py" in section, (
        "README.md's Architecture section never mentions check_heartbeat.py, the "
        "independent off-VPS process that monitors the bot's liveness and alerts "
        "on its own, separate from trader.py/notifier.py's trade-cycle path"
    )
