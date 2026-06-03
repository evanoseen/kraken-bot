"""Tests for the root logger configuration in `main.py`.

Pins:
- INFO level set
- Format string includes `%(name)s` so module names appear in every log line
- Both a stream handler (stdout) and a file handler (bot.log) are configured
- No bare `print()` calls exist in the trading modules
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
TRADING_MODULES = [
    REPO_ROOT / "main.py",
    REPO_ROOT / "trader.py",
    REPO_ROOT / "kraken_client.py",
    REPO_ROOT / "market_matcher.py",
    REPO_ROOT / "news_fetcher.py",
    REPO_ROOT / "pump_detector.py",
    REPO_ROOT / "listing_monitor.py",
    REPO_ROOT / "positions.py",
    REPO_ROOT / "config.py",
]


def test_main_module_uses_required_log_format():
    """main.py's basicConfig format string matches the Day 14 spec."""
    text = (REPO_ROOT / "main.py").read_text()
    assert "[%(asctime)s] %(levelname)s %(name)s: %(message)s" in text


def test_main_module_sets_info_level():
    """basicConfig is called at INFO level."""
    text = (REPO_ROOT / "main.py").read_text()
    assert "level=logging.INFO" in text


def test_main_module_configures_both_handlers():
    """Both StreamHandler (stdout) and FileHandler (bot.log) are wired up."""
    text = (REPO_ROOT / "main.py").read_text()
    assert "logging.StreamHandler" in text
    assert 'logging.FileHandler("bot.log")' in text


@pytest.mark.parametrize("path", TRADING_MODULES, ids=lambda p: p.name)
def test_no_bare_print_calls_in_trading_modules(path: Path):
    """No file in the trading layer should use bare print() — logger only."""
    if not path.exists():
        pytest.skip(f"{path.name} not present")
    text = path.read_text()
    # Strip docstrings + comments before scanning to avoid string-literal noise.
    code_lines = [
        line for line in text.splitlines()
        if not line.lstrip().startswith("#")
    ]
    joined = "\n".join(code_lines)
    matches = re.findall(r"(?<![\w.])print\s*\(", joined)
    assert not matches, f"{path.name} contains {len(matches)} bare print() call(s)"


def test_module_logger_name_resolves_via_getLogger():
    """logging.getLogger(__name__) produces a usable, named logger."""
    log = logging.getLogger("test_logging_config_smoke")
    assert log.name == "test_logging_config_smoke"
    assert isinstance(log, logging.Logger)
