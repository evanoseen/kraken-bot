"""Day 63: .env.example must document exactly the env vars the codebase reads.

Day 6 wrote .env.example once. Day 53 found (and fixed) a hardcoded
EXPECTED_FIELDS list in test_config.py that had silently drifted for a dozen
Config fields — the exact failure mode a *maintained* list is prone to. This
test avoids repeating that mistake: both sides are derived from the actual
source via AST, not from a list someone has to remember to update, so this
test can't itself go stale the way the list it's modeled after did.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONFIG_PY = REPO_ROOT / "config.py"
ENV_EXAMPLE = REPO_ROOT / ".env.example"

# Every top-level .py file that's part of the running bot (mirrors
# tests/test_logging_config.py's TRADING_MODULES scope, plus scripts/).
_SOURCE_FILES = sorted(REPO_ROOT.glob("*.py")) + sorted((REPO_ROOT / "scripts").glob("*.py"))


def _getenv_names_in_source(text: str) -> set[str]:
    """Every string literal passed as the first arg to an os.getenv(...) call
    in a source file, found via AST so comments/docstrings/formatting can't
    produce false positives the way a regex scan would."""
    names = set()
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getenv"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.add(node.args[0].value)
    return names


def _config_env_vars() -> set[str]:
    """Env vars read specifically in config.py — the Config dataclass's contract."""
    return _getenv_names_in_source(CONFIG_PY.read_text())


def _all_env_vars_in_repo() -> set[str]:
    """Env vars read anywhere in the bot's own source (Config or not) — some
    modules (blacklist.py, status.py, trade_logger.py) read os.getenv
    directly rather than through Config, and .env.example documents those
    too. This is the true 'is this var used anywhere' check."""
    names = set()
    for path in _SOURCE_FILES:
        names |= _getenv_names_in_source(path.read_text())
    return names


def _env_example_vars() -> set[str]:
    """Every KEY= line in .env.example (ignores comments and blank lines)."""
    names = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        match = re.match(r"^([A-Z][A-Z0-9_]*)=", line)
        if match:
            names.add(match.group(1))
    return names


def test_env_example_documents_every_config_var():
    """Everything Config.from_env() reads must be documented — this is the
    half of the contract that actually breaks the bot if it drifts."""
    missing = _config_env_vars() - _env_example_vars()
    assert not missing, f"config.py reads these but .env.example doesn't document them: {sorted(missing)}"


def test_env_example_has_no_orphaned_vars():
    """Nothing in .env.example should be dead — either it's read by config.py,
    or by some other module (blacklist.py/status.py/trade_logger.py all read
    os.getenv directly), but it must be read by *something*."""
    orphaned = _env_example_vars() - _all_env_vars_in_repo()
    assert not orphaned, f".env.example documents these but nothing in the codebase reads them: {sorted(orphaned)}"


def test_at_least_the_known_source_files_were_scanned():
    """Guards against the glob silently matching zero files (e.g. a future
    repo reorg moving config.py) and both tests above passing vacuously."""
    scanned_names = {p.name for p in _SOURCE_FILES}
    assert {"config.py", "blacklist.py", "status.py", "trade_logger.py"} <= scanned_names
