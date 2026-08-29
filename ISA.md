---
project: kraken-bot
phase: verify
started: 2026-05-20
updated: 2026-08-29
---

# Kraken Bot — Project ISA

This is the living articulation of the kraken-bot project. It is the system of record for what this bot is, what it must do, and how we verify done. Iteration on the bot is iteration on this file.

## Problem

A meme coin trading bot is running 24/7 on a Hetzner VPS with real CAD on the line, but the project has almost no engineering scaffolding: no tests, no project docs beyond a setup README, no observability beyond `print` statements, no kill switch, no runbook, no security policy, no project ISA. Three signal sources (news, pump, listings) all funnel into one `trader.py` function with mixed concerns. Without scaffolding, a single bad cycle, a stuck deploy, or a Kraken API change can take the bot down silently, and Evan can't show recruiters a portfolio-grade system, only a working prototype.

## Vision

A meme coin trading bot that a recruiter could clone, read, run, and admire. Code that is typed, tested, logged, monitored, and documented. A kill switch I trust. A runbook that survives me forgetting the SSH command. Trade history queryable as JSONL. Daily PnL summaries on demand. Drawdown circuit breakers. Telegram alerts on every trade. Deploys with one command. A README with an architecture diagram and a status badge that stays green. When someone asks "what have you shipped" — this is the answer.

## Out of Scope

- Trading anything other than Kraken CAD pairs
- Margin, futures, or leveraged trading (spot only)
- Custodial features for other users (single-user system)
- A web UI (CLI + logs + notifications are the interface)
- Backtesting framework (live forward testing only for now)
- Multi-account / multi-exchange routing
- Tax accounting (export trades, hand off to other tooling)
- Faking commits or any GitHub activity-inflation tactic

## Principles

- **Real-money discipline.** Every change that affects runtime behavior is dry-runnable before it ships live. `DRY_RUN=true` is sacred.
- **Observability before optimization.** You cannot improve what you cannot measure. Logs, metrics, and trade history come before strategy tuning.
- **Small, scoped, daily commits.** Iteration beats refactors. Backlog and journal live in the repo.
- **The bot earns trust by surviving boring days.** Resilience to rate limits, network blips, and stale data matters more than alpha.
- **Fail loud, recover fast.** Crashes are fine; silent failures are not. Heartbeats, retries with backoff, kill switches, and circuit breakers are first-class concerns.
- **The repo is the system of record.** Anything that exists only on the server is a future outage.

## Constraints

- Kraken REST API only (no WebSocket subscriptions yet)
- Python 3.8+ (per requirements.txt and the Hetzner image)
- Hetzner CX23 (1 vCPU, 4 GB RAM) — keep memory and compute light
- CAD-denominated account, ZCAD balance
- `.env` holds secrets and is never committed
- One systemd unit, one process — no microservices, no queues
- Anthropic Claude API for news signal (claude-opus-4-6)
- `MAX_TRADE_AMOUNT`, `DAILY_LOSS_LIMIT`, `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT` are user-tunable env vars and must not be hardcoded
- Code changes that affect live trading require local dry-run validation before deploy

## Goal

Operate a transparent, observable, resilient meme coin trading bot on Kraken CAD that ships a real engineering improvement every day, never silently fails, never trades outside its configured risk envelope, and serves as a portfolio-grade demonstration of Evan's ability to design and run a production system end-to-end.

## Criteria

This is a seed set. The Daily Iteration backlog (`DAILY_ITERATIONS.md`) will expand this list as each task lands. ID-stability rule applies: never re-number on edit.

### Operational

- [x] ISC-1: Bot runs as a systemd unit (`kraken-bot.service`) on Hetzner with `Restart=always`
- [x] ISC-2: Bot reads all secrets from `.env`; `.env` is gitignored
- [x] ISC-3: Daily loss limit (`DAILY_LOSS_LIMIT`) halts trading for the day when breached
- [x] ISC-4: Stop-loss (`STOP_LOSS_PCT`) and take-profit (`TAKE_PROFIT_PCT`) trigger per-position exits
- [x] ISC-5: A `KILL` file in the repo root cleanly stops the bot on the next cycle (Day 24)
- [x] ISC-6: A `last_run.txt` heartbeat exists and is updated at the end of each cycle (Day 21)
- [x] ISC-7: `OPS_RUNBOOK.md` exists with SSH, systemd, log, deploy, rollback, and triage procedures (Day 5, expanded through Day 74)

### Signals

- [x] ISC-8: News signals — Claude AI analyzes RSS headlines and emits `(coin, action, confidence, reasoning)` records
- [x] ISC-9: Pump signals — coins with ≥3x normal volume are flagged with a confidence scaled by spike size
- [x] ISC-10: New listing signals — Kraken blog RSS triggers an immediate buy on listing day
- [x] ISC-11: `STRATEGY.md` documents the three signal sources and their combination rules end to end (Day 4, kept current through Day 69)

### Trading

- [x] ISC-12: Open orders are cancelled at the start of each cycle to free funds
- [x] ISC-13: `MAX_TRADE_AMOUNT` caps per-trade CAD spend
- [x] ISC-14: Sells are skipped for coins not currently held
- [x] ISC-15: Positions (`entry_price`, `amount_cad`) are recorded on buy and removed on sell

### Observability

- [x] ISC-16: All trade events append one JSON object per trade to `trades.jsonl` (Day 20)
- [x] ISC-17: Every Kraken API method logs its latency (Day 22)
- [x] ISC-18: `scripts/daily_pnl.py` aggregates `trades.jsonl` into a daily PnL summary (Day 23, gained `--since`/`--until` Day 60)
- [x] ISC-19: A JSON status file is written each cycle with run timestamp, balance, holdings, last decision, errors (Day 45; shipped as `status.json`, not the originally-named `latest_status.json` — see Decisions)

### Quality

- [x] ISC-20: Pytest scaffold present and `pytest --collect-only` exits 0 (Day 9)
- [x] ISC-21: At least one test per module in `tests/` (Days 10-13, 77, 78 — every root `.py` module now has direct or near-direct coverage; `main.py` is exercised by `test_cli_flags.py`/`test_graceful_shutdown.py` rather than a file literally named `test_main.py`)
- [x] ISC-22: GitHub Actions runs `pytest` on push; README shows the badge (Day 13, `pip-audit` added Day 58)
- [x] ISC-23: `kraken_client.py` has type hints on every function (mypy clean) (Day 15, locked by `tests/test_kraken_client_types.py`)
- [x] ISC-24: `trader.py` has type hints on every function (mypy clean) (Day 16, locked by `tests/test_trader_types.py`)
- [x] ISC-25: Every function in `kraken_client.py` has a docstring (Day 15; remaining modules covered Day 67)

### Resilience

- [x] ISC-26: Every Kraken API call is wrapped in `@retry` with exponential backoff (Day 18)
- [x] ISC-27: A rate limiter enforces ≥1 second between Kraken API calls (Day 19)
- [x] ISC-28: Drawdown circuit breaker liquidates positions on a configurable session drawdown (Day 27; shipped default is `MAX_DRAWDOWN_PCT=0.20`, not the originally-conjectured 15% — see Decisions)

### Security

- [x] ISC-29: `SECURITY.md` documents API key storage, rotation, kill switch, network exposure, and incident response (Day 8, re-audited Days 58 and 75)
- [x] ISC-30: `.env.example` exists and lists every environment variable with a placeholder value (Day 6, locked in sync by `tests/test_env_example.py` since Day 63)

### Deploy

- [ ] ISC-31: `deploy/kraken-bot.service` matches the systemd unit running on the VPS
- [x] ISC-32: `scripts/deploy.sh` runs tests, rsyncs the repo, restarts the service, and verifies the heartbeat advanced (Day 57 — rsync instead of the originally-conjectured scp, so `.env` on the server is never clobbered)

### Anti-criteria

- [x] ISC-33: Anti: no auto-commit cron, no GitHub-activity-inflation script, no fake-commit automation lives in this repo
- [x] ISC-34: Anti: no secret values (`KRAKEN_API_KEY`, `KRAKEN_PRIVATE_KEY`, `ANTHROPIC_API_KEY` actual values) appear in any committed file
- [x] ISC-35: Anti: the bot does not trade outside CAD pairs (enforced in `pump_detector.py`'s quote filter and `kraken_client.get_tradable_coins`)
- [x] ISC-36: Anti: live trading never runs without `DAILY_LOSS_LIMIT` configured (`Config.validate()`, Day 73, rejects `DAILY_LOSS_LIMIT <= 0` at startup)
- [x] ISC-37: Anti: code that affects runtime behavior is not deployed without a local dry-run (documented in `OPS_RUNBOOK.md`'s pre-deploy checklist)

### Antecedent

- [x] ISC-38: Antecedent: `DAILY_ITERATIONS.md` has an open task for any unchecked ISC in this list (ISC-31 maps to Day 56, currently blocked on VPS SSH access — see Decisions; this criterion is a standing discipline, not a one-time check, and should be re-verified whenever a new unchecked ISC is added)

## Test Strategy

| isc | type | check | threshold | tool |
|-----|------|-------|-----------|------|
| ISC-1 | systemd | `systemctl is-active kraken-bot` returns `active` | `active` | `ssh + systemctl` |
| ISC-2 | git | `.env` not tracked; gitignore contains `^\.env$` | yes | `git ls-files \| grep ; grep .gitignore` |
| ISC-3 | log | daily-loss-limit warning fires in `journalctl` when threshold crossed | observed | `journalctl -u kraken-bot \| grep "Daily loss limit"` |
| ISC-4 | log | stop-loss / take-profit log lines appear when triggered | observed | `journalctl \| grep "STOP-LOSS\\|TAKE-PROFIT"` |
| ISC-5 | bash | `touch KILL` causes next cycle to exit cleanly | observed | manual + log |
| ISC-6 | file | `last_run.txt` mtime within last 2 × `RUN_INTERVAL_MINUTES` | within window | `stat + date` |
| ISC-7 | file | `OPS_RUNBOOK.md` exists with 6 sections | ≥6 sections | `Read + grep ^##` |
| ISC-8..15 | code | feature behavior visible in `trader.py` and signal modules | code present | `Grep` |
| ISC-16 | file | `trades.jsonl` parses as JSONL | each line valid | `python3 json.loads` |
| ISC-17 | log | every Kraken API method emits a latency log | observed | `journalctl \| grep "kraken\\..*took"` |
| ISC-18 | bash | `python3 scripts/daily_pnl.py` exits 0 and prints a table | exit 0 | Bash |
| ISC-19 | file | `latest_status.json` has 5 fields after a cycle | 5 keys | `python3 + json` |
| ISC-20..22 | bash | pytest collects and passes; GH Actions green | exit 0 | `pytest ; gh run list` |
| ISC-23..24 | bash | `mypy` clean on the named file | 0 errors | `mypy` |
| ISC-25 | bash | every function has a docstring | 100% | `ast.parse` |
| ISC-26..27 | code | decorators / rate limiter present and unit-tested | tests pass | `pytest` |
| ISC-28 | code | drawdown breaker unit test fires liquidation on 16% sim drawdown | test pass | `pytest` |
| ISC-29..30 | file | `SECURITY.md` and `.env.example` exist with required content | yes | `Read + grep` |
| ISC-31 | diff | `deploy/kraken-bot.service` matches what is on the VPS | identical | `ssh cat + diff` |
| ISC-32 | bash | `./scripts/deploy.sh` end to end exits 0 on no-op change | exit 0 | Bash |
| ISC-33 | scan | no auto-commit script anywhere in repo | none | `grep -r "git commit" scripts/` |
| ISC-34 | scan | no committed file contains a real secret-shaped value | none | `git log -p \| grep` |
| ISC-35 | code | trading pairs restricted to CAD | enforced | `Grep` |
| ISC-36 | code | startup refuses live trading without `DAILY_LOSS_LIMIT` | enforced | unit test |
| ISC-37 | discipline | OPS_RUNBOOK deploy step requires dry-run validation | documented | `Read` |
| ISC-38 | cross-ref | every unchecked ISC maps to a DAILY_ITERATIONS task | 100% | manual |

## Features

| name | satisfies | depends_on | parallelizable |
|------|-----------|------------|----------------|
| operational hardening | ISC-5, ISC-6, ISC-7 | none | yes |
| docs & runbook | ISC-7, ISC-11, ISC-29, ISC-30 | none | yes |
| observability layer | ISC-16, ISC-17, ISC-18, ISC-19 | none | yes |
| quality bar | ISC-20..25 | observability | partial |
| resilience | ISC-26, ISC-27, ISC-28 | observability | no |
| deploy automation | ISC-31, ISC-32 | resilience | no |

## Decisions

- 2026-05-20 **decision:** Seeded the project ISA tonight rather than running a full Interview workflow. Reason: Day 2 done-when only requires the six core sections + frontmatter; a full Interview run would burn the day's budget. Refinement will happen organically as each daily iteration lands.
- 2026-05-20 **decision:** Anti-criteria include "no auto-commit / no fake-activity script" as an explicit guardrail. Reason: the original ask was for GitHub activity inflation; the ISA names what we will not become.
- 2026-05-20 **decision:** Existing already-built behavior is marked `[x]` (operational + signals + trading core). Reason: ISCs describe end-state, not new work; the bot already operates many of these — they belong in Verification immediately.
- 2026-05-20 **decision:** `ISC-38` (antecedent) binds the ISA to `DAILY_ITERATIONS.md`. Reason: the two artifacts must stay in sync — every gap names a backlog item.
- 2026-08-29 **decision:** This pass checks off the original 38 ISCs against reality and fixes the two places reality diverged from the Day-2 conjecture (`status.json` vs. the originally-named `latest_status.json`; `MAX_DRAWDOWN_PCT=0.20` shipped vs. the originally-conjectured 15%), but does **not** add new ISCs for every feature shipped since Day 2 (trailing stop, confidence-scaled sizing, config validation, positions reconciliation, coverage tooling, Dependabot, blacklist/cooldown/headline-cache, and more). Reason: this file's own first line says "iteration on the bot is iteration on this file," and that discipline broke down completely for 78 days — the honest fix today is closing the gap that already exists, not compounding scope into a same-day rewrite of the whole ISC set. A proper "ISA v2: define ISCs for Days 18-79" pass is queued as its own backlog task so it gets the attention a from-scratch criteria set deserves, instead of being bolted onto a catch-up.
- 2026-08-29 **decision:** Verification entries now cite function/file names instead of line numbers. Reason: the original Verification section cited exact line numbers (`trader.py:168`, etc.) and at least one had already gone factually wrong by Day 62 (the formula it described was replaced) well before anyone noticed — the same class of drift this project has independently rediscovered and fixed in READMEs, STRATEGY.md, and SECURITY.md on Days 55, 63, 64, 66, and 75. A function name survives a refactor; a line number is a promise that decays the moment the file changes.

## Changelog

- 2026-05-20 **seeded** | conjectured: "A meme coin bot only needs strategy code." | refuted by: "Three commits in two months, no tests, no runbook, no observability — the surface that fails first is the engineering scaffold, not the strategy." | learned: The project's risk surface is operational and observational, not just algorithmic. | criterion now: 38 ISCs cover ops, signals, trading, observability, quality, resilience, security, deploy, anti-criteria, and antecedent — the engineering scaffold IS the ISA.
- 2026-08-29 **re-verified after 78 days dark** | conjectured (implicitly, by neglect): "Once the ISA is seeded, the daily-iteration backlog is enough to keep the project honest on its own." | refuted by: this file's own frontmatter — `updated: 2026-05-20`, unchanged through 76 subsequent days of shipped work, while its Vision paragraph kept describing a kill switch, Telegram alerts, JSONL history, drawdown breakers, and a one-command deploy as aspirational, all of which had shipped and been verified working weeks or months earlier. `DAILY_ITERATIONS.md` and `JOURNAL.md` turned out to be necessary but not sufficient — they recorded that work happened, but nothing forced the record of *what the project actually is* to stay current, and the gap wasn't visible from inside any single day's task. | learned: A "living" document doesn't stay alive by being declared one; it needs the same kind of periodic, scheduled re-audit this project has now applied to every other doc (README Day 64, STRATEGY.md Day 66, SECURITY.md Day 75, `.env.example` continuously via Day 63's test) — and the highest-leverage one, the actual system of record, went the longest without it precisely because nothing was pointed at it. | criterion now: 34 of 38 ISCs checked with current, function-level (not line-number) verification; ISC-31 (systemd unit in repo) remains genuinely open, correctly mapped to Day 56; two ISCs' wording corrected to match what was actually shipped rather than the original conjecture.

## Verification

Re-verified Day 79 (2026-08-29) — 34 of 38 ISCs updated from unchecked to checked with current evidence. References are by function/file name rather than line number on purpose: the Day-2 version of this section cited exact line numbers (`trader.py:168`, etc.) that had already drifted false by Day 62 (the sizing formula they described was replaced entirely) — the same brittleness this project has hit and fixed in READMEs and other docs repeatedly (Days 55, 63, 64, 66, 75). A function name survives a refactor; a line number doesn't.

- ISC-1: `systemctl is-active kraken-bot` returns `active` on `root@204.168.204.221` (per project memory and prior verification on Day 1 setup — not re-checked today, no current VPS access in this environment)
- ISC-2: `cat .gitignore` shows `.env`; `git ls-files | grep "^\.env$"` returns nothing
- ISC-3: `trader.run_trading_cycle`'s daily-loss gate compares `_starting_balance - balance` against `cfg.daily_loss_limit`
- ISC-4: `trader.check_exit_conditions`'s stop-loss/take-profit branches, now joined by a third: trailing stop (Day 69)
- ISC-5: `kill_switch.kill_switch_active()`, checked at the top of `trader.run_trading_cycle`
- ISC-6: `heartbeat.write_heartbeat()`, called from `main.py`'s `run_cycle()` after every trading cycle
- ISC-7: `OPS_RUNBOOK.md` — 9 numbered sections as of Day 74, well past the original 6
- ISC-8: `market_matcher.analyze_news_for_trades` produces signal records, called from `trader.run_trading_cycle`
- ISC-9: `pump_detector.find_pumping_coins`, confidence derived in `trader.py` from spike size — both now have direct unit tests (Day 77)
- ISC-10: `listing_monitor.check_new_listings` triggers immediate buy — now has direct unit tests (Day 77)
- ISC-11: `STRATEGY.md`'s "Signal sources" and "The trading cycle" sections
- ISC-12: `trader.run_trading_cycle` cancels open orders at cycle start
- ISC-13: `trader.size_position()` (Day 62) — replaced the original `MAX_TRADE_AMOUNT * confidence` multiplier with an explicit linear scale over `[MIN_CONFIDENCE, 1.0]`; documented in `STRATEGY.md`
- ISC-14: `trader.run_trading_cycle` skips sells for coins not in `holdings`
- ISC-15: `positions.record_buy` and `positions.remove_position` — now have direct unit tests at 100% coverage (Day 78)
- ISC-16: `positions.log_trade` writes one JSON object per line to `trades.jsonl`, verified by `tests/test_positions.py` and `tests/test_log_trade_jsonl.py`
- ISC-17: `kraken_client._call_private`/`_call_public` log `kraken.<kind>/<endpoint> took N.NNs`, verified by `tests/test_kraken_latency_logging.py`
- ISC-18: `python3 scripts/daily_pnl.py` exits 0 and prints a table; `--since`/`--until` added Day 60
- ISC-19: `status.write_status()`, called from `trader.run_trading_cycle` after every cycle; writes `status.json` (path from `STATUS_FILE`, default changed from the ISA's original `latest_status.json` — see Decisions)
- ISC-20: `pytest --collect-only` exits 0 (434+ tests as of Day 78)
- ISC-21: every root module has direct or near-direct test coverage — `make coverage` shows every file ≥91% except `kraken_client.py` (75%) and `trader.py` (82%), both queued as follow-up work
- ISC-22: `.github/workflows/test.yml` runs pytest + `pip-audit` on every push; README badge confirmed resolving Day 64
- ISC-23: `tests/test_kraken_client_types.py` pins `mypy --ignore-missing-imports kraken_client.py` at 0 errors
- ISC-24: `tests/test_trader_types.py` pins the same for `trader.py`
- ISC-25: `tests/test_config_notifier_status_blacklist_types.py` and manual docstring pass (Day 67) cover the remaining modules; `kraken_client.py`'s own docstrings date to Day 15
- ISC-26: `kraken_client._retry_kraken` (`tenacity`) decorates `_call_private`/`_call_public`
- ISC-27: `kraken_client._rate_limit()`, verified by `tests/test_kraken_rate_limit.py`
- ISC-28: `trader.run_trading_cycle`'s drawdown check against `cfg.max_drawdown_pct` (default `0.20`), verified by `tests/test_drawdown.py`
- ISC-29: `SECURITY.md`, 6 numbered sections plus a hardening backlog, re-audited Days 58 and 75
- ISC-30: `.env.example`, kept in exact sync with the codebase by `tests/test_env_example.py` (Day 63)
- ISC-31: not yet done — `deploy/kraken-bot.service` doesn't exist in the repo; blocked on VPS SSH access this environment doesn't have (tracked as Day 56)
- ISC-32: `scripts/deploy.sh` — test, rsync, restart, poll the heartbeat until it advances or times out
- ISC-33: `grep -r "git commit" scripts/` returns nothing; no cron/auto-commit script exists anywhere in the repo
- ISC-34: `tests/test_env_example.py` and manual history review — no real secret-shaped value has ever been committed
- ISC-35: `pump_detector.find_pumping_coins` only builds `pair_info` for `quote in ("ZCAD", "CAD")`; `kraken_client.get_tradable_coins` filters to CAD/USD pairs
- ISC-36: `Config.validate()` (Day 73) raises `ValueError` at startup if `daily_loss_limit <= 0`, enforced via `health.run_checks()`
- ISC-37: `OPS_RUNBOOK.md` section 4's pre-deploy checklist requires a `DRY_RUN=true` dry-run cycle before every deploy
- ISC-38: the one remaining unchecked ISC (ISC-31) has an open, correctly-mapped `DAILY_ITERATIONS.md` entry (Day 56)
