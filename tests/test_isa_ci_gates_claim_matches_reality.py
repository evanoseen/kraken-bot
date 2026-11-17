"""Day 150: three places in ISA.md all understated `.github/workflows/test.yml`'s
real CI gate list — the ISC-22 checklist bullet, the ISC-22 Verification-table
row, and the ISC-44 checklist bullet each still named only `pytest` (or
`pytest` + `pip-audit`), even though the workflow has run five gates (pytest +
coverage, pip-audit, bandit, shellcheck, yamllint) since Day 116. Day 115's
own `DAILY_ITERATIONS.md` entry explicitly flagged ISC-22 as going stale when
`shellcheck` was added and deferred the fix to a dedicated ISA re-audit pass —
but the two re-audit passes since (Days 146, 147) each fixed a different row
and missed this one, so the gap sat for 35 days.

Derives the real gate list from test.yml's own single-line `run:` steps
(skipping the multi-line "Install dependencies" step) instead of hardcoding
it, so a future gate addition or removal fails this test immediately rather
than waiting for another manual sweep.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ISA = REPO_ROOT / "ISA.md"
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"

# Each real gate step's `run:` line is single-line ("run: <command>"); the
# one multi-line step ("Install dependencies", `run: |`) is deliberately not
# matched by requiring a command on the same line.
RUN_COMMAND_PATTERN = re.compile(r"^\s+run: (\S+)", re.MULTILINE)


def _real_gate_tools() -> set[str]:
    commands = RUN_COMMAND_PATTERN.findall(WORKFLOW.read_text())
    return {command.split("/")[-1] for command in commands if command != "|"}


def test_workflow_has_more_than_two_gates():
    # sanity check that the extraction method is actually finding steps
    assert len(_real_gate_tools()) >= 5


def test_isa_ci_gate_claims_match_reality():
    real_tools = _real_gate_tools()
    isa_text = ISA.read_text()

    checklist_bullet = re.search(r"- \[x\] ISC-22:.*", isa_text)
    verification_row = re.search(r"- ISC-22: `\.github/workflows/test\.yml`.*", isa_text)
    isc44_bullet = re.search(r"- \[x\] ISC-44:.*", isa_text)

    assert checklist_bullet, "Expected an ISC-22 checklist bullet in ISA.md's Criteria section"
    assert verification_row, "Expected an ISC-22 row in ISA.md's Verification section"
    assert isc44_bullet, "Expected an ISC-44 checklist bullet in ISA.md's Criteria section"

    for label, match in (
        ("ISC-22 checklist bullet", checklist_bullet),
        ("ISC-22 Verification row", verification_row),
        ("ISC-44 checklist bullet", isc44_bullet),
    ):
        line = match.group(0)
        for tool in real_tools:
            assert tool in line, (
                f"ISA.md's {label} doesn't mention `{tool}`, but test.yml actually runs it as a CI gate: {line!r}"
            )
