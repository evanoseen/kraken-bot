"""Day 117: every local markdown link in the project's docs must resolve.

Days 108/109/113 swept for stale "Day N" cross-references and stale
revisit-policy comments by hand, one-time. Days 115/116 gave shell scripts
and YAML files a permanent static-analysis gate instead of a one-time sweep.
This test closes the same gap for the project's seven root-level markdown
docs (README.md, STRATEGY.md, OPS_RUNBOOK.md, SECURITY.md, ISA.md,
DAILY_ITERATIONS.md, JOURNAL.md): a `[text](path)` link to a local file is
silent-failure-prone the same way `.env.example` drift and README test-count
drift were — nothing short of a human clicking the link ever notices a typo
or a renamed/deleted target, and GitHub renders a dead markdown link with no
warning at all.

Scoped to local file links only (no network calls, so no CI flakiness):
skips `http(s)://` and `mailto:` targets, and skips pure in-page anchors
(`#section`). Strips fenced and inline code spans before scanning so a link
*example* inside a code block (e.g. a grep pattern ending in `](...)`) can't
be mistaken for a real link.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

MARKDOWN_FILES = sorted(REPO_ROOT.glob("*.md"))

_FENCED_CODE_BLOCK = re.compile(r"```.*?```", re.DOTALL)
_INLINE_CODE_SPAN = re.compile(r"`[^`\n]*`")
_MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


def _strip_code(text: str) -> str:
    """Remove fenced and inline code spans so link-shaped text inside a
    code example (backticks, grep patterns, etc.) is never scanned."""
    text = _FENCED_CODE_BLOCK.sub("", text)
    return _INLINE_CODE_SPAN.sub("", text)


def _local_link_targets(markdown_file: Path) -> list[str]:
    """Every local-file link target in one markdown file, with code spans
    stripped out first and any `#anchor` fragment removed."""
    text = _strip_code(markdown_file.read_text())
    targets = []
    for raw_target in _MARKDOWN_LINK.findall(text):
        target = raw_target.strip()
        if not target or target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        targets.append(target.split("#", 1)[0])
    return targets


def test_every_local_markdown_link_resolves_to_a_real_path():
    broken = []
    for markdown_file in MARKDOWN_FILES:
        for target in _local_link_targets(markdown_file):
            resolved = (markdown_file.parent / target).resolve()
            if not resolved.exists():
                broken.append(f"{markdown_file.name} -> {target}")

    assert not broken, (
        "Found markdown link(s) pointing at a path that doesn't exist "
        f"(dead link, GitHub won't warn about this on its own): {broken}"
    )


def test_scan_actually_finds_the_known_local_links():
    """Guards against the regex silently matching zero links (e.g. a future
    docs rewrite changing link syntax), which would pass the test above
    vacuously the same way test_readme_test_count.py's sibling check does."""
    total = sum(len(_local_link_targets(f)) for f in MARKDOWN_FILES)
    assert total >= 10, (
        f"Expected at least 10 local markdown links across {len(MARKDOWN_FILES)} "
        f"docs (README.md alone has 10+), found {total} -- scan may be broken."
    )
