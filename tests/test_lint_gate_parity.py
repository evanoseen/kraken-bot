"""Day 153: Day 150 locked ISA.md's ISC-22/ISC-44 claims about
`.github/workflows/test.yml`'s real CI gate list against the workflow file
itself (`tests/test_isa_ci_gates_claim_matches_reality.py`) — but four other
places make the identical "four non-pytest gates" claim and none of them
were covered by that lock test or any other: the `Makefile`'s own `lint`
target comment, `scripts/deploy.sh`'s lint-gates comment/echo, README.md's
"CI on every push" bullet, and OPS_RUNBOOK.md's deploy-flow description.
All four currently list the real four tools correctly (pip-audit, bandit,
shellcheck, yamllint) with no drift found — this is a missing-lock gap, not
a stale-claim one, the same shape Day 151/152 found in ISA.md's own Extended
section and Decisions log.

Derives the real non-pytest gate list from test.yml's own `run:` steps
(same method as the Day 150 test) so a future CI gate addition or removal
fails here immediately, across all four surfaces at once, instead of
leaving three of them to silently drift the next time only one place gets
updated.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "test.yml"
MAKEFILE = REPO_ROOT / "Makefile"
DEPLOY_SH = REPO_ROOT / "scripts" / "deploy.sh"
README = REPO_ROOT / "README.md"
OPS_RUNBOOK = REPO_ROOT / "OPS_RUNBOOK.md"

# Each real gate step's `run:` line is single-line ("run: <command>"); the
# one multi-line step ("Install dependencies", `run: |`) is deliberately not
# matched by requiring a command on the same line. Mirrors the extraction
# in tests/test_isa_ci_gates_claim_matches_reality.py.
RUN_COMMAND_PATTERN = re.compile(r"^\s+run: (\S+)", re.MULTILINE)

# `pip-audit` runs as a CLI command in test.yml and deploy.sh/README/
# OPS_RUNBOOK, but as `python -m pip_audit` in the Makefile — both names
# refer to the same real gate.
ALIASES = {"pip-audit": ("pip-audit", "pip_audit")}


def _real_non_pytest_gates() -> set[str]:
    commands = RUN_COMMAND_PATTERN.findall(WORKFLOW.read_text())
    tools = {command.split("/")[-1] for command in commands if command != "|"}
    tools.discard("pytest")
    return tools


def _assert_text_names_every_gate(label: str, text: str, gates: set[str]) -> None:
    for gate in gates:
        names = ALIASES.get(gate, (gate,))
        assert any(name in text for name in names), (
            f"{label} is missing the real CI gate {gate!r} (checked for "
            f"{names!r}) — a gate was added to test.yml without updating {label}"
        )


def test_workflow_has_four_non_pytest_gates():
    # sanity check that the extraction method is actually finding steps
    assert len(_real_non_pytest_gates()) == 4


def test_makefile_lint_target_matches_reality():
    gates = _real_non_pytest_gates()
    text = MAKEFILE.read_text()
    match = re.search(r"\nlint:\n((?:\t.*\n?)+)", text)
    assert match, "Expected a 'lint:' target with an indented recipe in the Makefile"
    _assert_text_names_every_gate("Makefile's lint: target", match.group(1), gates)


def test_deploy_sh_lint_gates_match_reality():
    gates = _real_non_pytest_gates()
    text = DEPLOY_SH.read_text()
    match = re.search(r"Running lint gates.*?\n\n", text, re.DOTALL)
    assert match, "Expected a 'Running lint gates' block in scripts/deploy.sh"
    _assert_text_names_every_gate("scripts/deploy.sh's lint-gates block", match.group(0), gates)


def test_readme_ci_bullet_matches_reality():
    gates = _real_non_pytest_gates()
    match = re.search(r"- \*\*CI on every push\*\*.*", README.read_text())
    assert match, "Expected a 'CI on every push' bullet in README.md"
    _assert_text_names_every_gate("README.md's 'CI on every push' bullet", match.group(0), gates)


def test_ops_runbook_deploy_description_matches_reality():
    gates = _real_non_pytest_gates()
    match = re.search(r"This runs the test suite, then the Day \d+ lint gates \([^)]*\)", OPS_RUNBOOK.read_text())
    assert match, "Expected a 'This runs the test suite, then the Day N lint gates (...)' sentence in OPS_RUNBOOK.md"
    _assert_text_names_every_gate("OPS_RUNBOOK.md's deploy-flow description", match.group(0), gates)
