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

---

## Day 4, 2026-05-23

**Shipped:** Authored `STRATEGY.md` end to end. Every signal source has its own section grounded in the actual code: what it watches, what it measures, what it emits, why it works, and what it deliberately doesn't do. Listing monitor pulls the Kraken blog RSS, pump detector hunts obscure CAD pairs under $5M daily volume with >=3x intraday spike, and news + social layer blends six RSS feeds with ~50 Nitter accounts before sending to Claude Opus 4.6 for signal extraction. Confidence math is named explicitly (pump uses `min(0.65 + spike/50, 0.95)`; news uses Claude output filtered by `MIN_CONFIDENCE`). The trading cycle is documented as a Mermaid flowchart with the six stages, and exit logic is laid out in a table covering stop loss, take profit, and news-driven sells. Closed with a "known structural weaknesses" section that maps each gap to a future backlog day so the doc stays honest.

**Surprised by:** How asymmetric the strategy actually is. Entry is sophisticated — three independent catalyst-driven signals — but exit is just two fixed percentages off entry price. No trailing stop, no time-based exit, no signal-driven liquidation outside the held set. Writing it down made the imbalance obvious in a way the code never did.

**Next:** Day 5, write `OPS_RUNBOOK.md` covering SSH access, systemd commands, log inspection, deploy, rollback, and triage steps.

---

## Day 5, 2026-05-25

**Shipped:** Authored `OPS_RUNBOOK.md` with nine sections — quick-reference card, SSH access, systemd commands, log inspection (both `journalctl` and the `bot.log` file logger), deploy procedure (with a hard warning about `scp -r` clobbering `.env` and an `rsync --exclude` fix), rollback procedure (git worktree path as preferred, in-place revert as backup, emergency stop as last resort), triage (organized by real symptoms: no trades for hours, failed state, Kraken API errors, position mismatch, "stop trading right now"), a server file map, an env-var reference table with live defaults, and a post-change verification trio.

**Surprised by:** The deploy procedure I had in project memory (`scp -r /Users/evanoseen/kraken-bot root@204.168.204.221:/root/`) silently clobbers `.env` on the server every time. That's a real footgun and the runbook now flags it with an `rsync --exclude='.env'` alternative. Future me will thank present me.

**Next:** Day 6, write `.env.example` listing every environment variable in `config.py` with placeholder values and per-line comments.
