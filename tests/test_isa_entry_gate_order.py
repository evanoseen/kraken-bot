"""Day 151: ISA.md's new ISC-46/ISC-47 entries claim a specific check order
inside `trader.run_trading_cycle`'s per-signal loop — blacklist first, then
the per-coin trade cap, then cooldown. That order is currently true (read
directly from `trader.py`), but nothing stopped it from silently drifting
the way other ISA claims have (Days 126/127/129/134/146/147/150), since the
three checks are independent `if ... continue` guards a future edit could
reorder without breaking any existing test.

Derives the real order from `trader.py`'s source (the line position of each
guard call) rather than hardcoding it, so a future reorder fails this test
immediately instead of waiting for a future manual ISA re-audit.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"
TRADER = REPO_ROOT / "trader.py"

GUARD_CALLS = ("is_blacklisted(", "coin_at_cap(", "is_on_cooldown(")


def _real_guard_order() -> list[str]:
    source = TRADER.read_text()
    positions = [(source.index(call), call) for call in GUARD_CALLS]
    positions.sort()
    return [call.rstrip("(") for _, call in positions]


def test_all_three_guards_present_exactly_once():
    source = TRADER.read_text()
    for call in GUARD_CALLS:
        assert source.count(call) == 1, (
            f"expected exactly one `{call}` guard call in trader.py's per-signal loop, "
            f"found {source.count(call)}"
        )


def test_real_guard_order_is_blacklist_then_cap_then_cooldown():
    assert _real_guard_order() == ["is_blacklisted", "coin_at_cap", "is_on_cooldown"]


def test_isa_claims_match_real_guard_order():
    real_order = _real_guard_order()
    isa_text = ISA.read_text()

    isc46_row = re.search(r"^- ISC-46: .*$", isa_text, re.MULTILINE)
    isc47_row = re.search(r"^- ISC-47: .*$", isa_text, re.MULTILINE)
    assert isc46_row, "Expected an ISC-46 row in ISA.md's Verification section"
    assert isc47_row, "Expected an ISC-47 row in ISA.md's Verification section"

    assert "first entry-gate check" in isc46_row.group(0)
    assert real_order[0] == "is_blacklisted", (
        "ISA.md's ISC-46 Verification row claims the blacklist check runs first "
        f"in the per-signal loop, but trader.py's real guard order is {real_order}"
    )

    assert "after the blacklist and per-coin-cap checks" in isc47_row.group(0)
    assert real_order.index("is_on_cooldown") > real_order.index("is_blacklisted"), (
        "ISA.md's ISC-47 Verification row claims cooldown runs after blacklist, "
        f"but trader.py's real guard order is {real_order}"
    )
    assert real_order.index("is_on_cooldown") > real_order.index("coin_at_cap"), (
        "ISA.md's ISC-47 Verification row claims cooldown runs after the per-coin "
        f"cap, but trader.py's real guard order is {real_order}"
    )
