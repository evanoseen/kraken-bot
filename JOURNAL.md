# Iteration Journal

One entry per day. Capture: what shipped, what surprised, what's next.

---

## Day 1, 2026-05-19

**Shipped:** The daily iteration system itself. Created `DAILY_ITERATIONS.md` (30 curated tasks across docs, tests, refactors, observability, features, ops), `JOURNAL.md` (this file), and `scripts/daily.sh` (deterministic picker that prints today's task by day index). Updated `README.md` to surface the new workflow.

**Surprised by:** How much legitimate engineering work the bot was missing. Zero tests, zero docstrings on the API client, no kill switch, no project ISA, no runbook, no logging beyond `print()`. The 30 task backlog wrote itself once I cataloged the gaps.

**Next:** Day 2, seed a project `ISA.md` at the repo root with the twelve section structure from PAI doctrine.

---

## Day 2, 2026-05-20

**Shipped:** Seeded `ISA.md` at the repo root with the full twelve-section PAI template — Problem, Vision, Out of Scope, Principles, Constraints, Goal, Criteria, Test Strategy, Features, Decisions, Changelog, Verification. Frontmatter sets `project: kraken-bot, phase: observe`. The Criteria section names 38 ISCs across operations, signals, trading, observability, quality, resilience, security, deploy, anti-criteria, and antecedent. Existing already-built behavior is marked `[x]` with file:line evidence in the Verification section; pending ISCs map one-to-one to entries in `DAILY_ITERATIONS.md`.

**Surprised by:** How much of the bot is already done from an end-state perspective once you write the criteria down. 11 of 38 ISCs (operational core, all three signal sources, trading core) were already passing. The gap is engineering scaffold, not features.

**Next:** Day 3, add a docstring to every function in `kraken_client.py`.

---

## Day 3, 2026-05-21

**Shipped:** Added docstrings to the two undocumented functions in `kraken_client.py` — `get_client` (build the krakenex REST client) and `get_balance` (return CAD balance with USD fallback). Each docstring covers args, returns, and side effects per the backlog spec. The AST probe `all(ast.get_docstring(f) for f in funcs)` now returns `True` across the whole file.

**Surprised by:** Five of seven functions in `kraken_client.py` already had docstrings — they just weren't on the ones that needed them most (the client constructor and the balance call, both first-touch surfaces for a reader). The gap was at the boundary, not in the body.

**Next:** Day 4, write `STRATEGY.md` documenting the three signal sources (news, pump, listings) end to end.
