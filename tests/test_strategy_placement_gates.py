"""Day 160: STRATEGY.md's "Placement" stage must list every skip gate
`trader.py`'s generic signal loop actually has.

STRATEGY.md's stage-8 "Placement" section (and the mermaid overview above
it) only ever documented two of the generic signal loop's skip conditions:
"sells on coins not currently held are skipped" and "coins without a price
quote are skipped." Reading `trader.py`'s real `for signal in signals:`
loop top to bottom turned up five more `if ...: continue` gates that were
never mentioned anywhere in STRATEGY.md at all: the blacklist (Day 39), the
per-coin trade cap (Day 41), the post-trade cooldown window, the
`MAX_OPEN_POSITIONS` ceiling on buys, and the `MIN_TRADE_AMOUNT` trade-size
floor (Day 46) — a reader trying to understand why a signal that looked
valid never produced a trade was missing most of the real answer.

This locks two things so the gap (and its fix) can't silently drift again:

1. The *count* of `if ...: continue` gates inside the signal loop, derived
   from `trader.py`'s own AST rather than hardcoded, must match the number
   of gates this test knows about below. If a future day adds or removes a
   gate without updating this file, the count mismatches and the test names
   the drift directly instead of passing vacuously.
2. Each known gate's real source substring must still be present in
   `trader.py`, and a plain-English description of it must still be present
   in STRATEGY.md's Placement section — so a rename on either side fails
   loudly instead of the doc quietly going stale the way it already had.
"""
from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRADER_PY = REPO_ROOT / "trader.py"
STRATEGY_MD = REPO_ROOT / "STRATEGY.md"

# (real source substring in trader.py's signal loop, plain-English phrase
# that must appear in STRATEGY.md's Placement section), one pair per real
# `if ...: continue` skip gate, in the order they run.
GATES = [
    ('if action == "sell" and coin not in holdings:', "Sells on coins not currently held are skipped"),
    ("is_blacklisted(coin)", "Blacklisted coins are skipped"),
    ("coin_at_cap(coin, cfg.max_trades_per_coin)", "per-coin trade cap"),
    ("is_on_cooldown(coin, cfg.trade_cooldown_minutes)", "cooldown window are skipped"),
    ("len(holdings) >= cfg.max_open_positions", "MAX_OPEN_POSITIONS"),
    ("if not price:", "without a price quote are skipped"),
    ("trade_amount < cfg.min_trade_amount", "below `MIN_TRADE_AMOUNT` are skipped"),
]


def _placement_section_text() -> str:
    text = STRATEGY_MD.read_text()
    start = text.index('**8. Placement.**')
    end = text.index("\n\n---", start)
    return text[start:end]


def _count_signal_loop_skip_gates() -> int:
    tree = ast.parse(TRADER_PY.read_text())
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and node.target.id == "signal"
        ):
            return sum(
                1
                for sub in ast.walk(node)
                if isinstance(sub, ast.If) and sub.body and isinstance(sub.body[-1], ast.Continue)
            )
    raise AssertionError("could not find 'for signal in signals:' loop in trader.py")


def test_every_known_gate_still_exists_in_both_files():
    trader_src = TRADER_PY.read_text()
    placement = _placement_section_text()
    missing = []
    for code_substring, doc_phrase in GATES:
        if code_substring not in trader_src:
            missing.append(f"trader.py no longer contains {code_substring!r}")
        if doc_phrase not in placement:
            missing.append(f"STRATEGY.md's Placement section no longer contains {doc_phrase!r}")
    assert not missing, "\n".join(missing)


def test_gate_count_matches_the_real_signal_loop():
    real_count = _count_signal_loop_skip_gates()
    assert real_count == len(GATES), (
        f"trader.py's 'for signal in signals:' loop has {real_count} "
        f"'if ...: continue' skip gates, but this test (and STRATEGY.md's "
        f"Placement section) only account for {len(GATES)} -- a gate was "
        "added or removed without updating both."
    )
