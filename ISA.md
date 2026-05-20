---
project: kraken-bot
phase: observe
started: 2026-05-20
updated: 2026-05-20
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
- [ ] ISC-5: A `KILL` file in the repo root cleanly stops the bot on the next cycle
- [ ] ISC-6: A `last_run.txt` heartbeat exists and is updated at the end of each cycle
- [ ] ISC-7: `OPS_RUNBOOK.md` exists with SSH, systemd, log, deploy, rollback, and triage procedures

### Signals

- [x] ISC-8: News signals — Claude AI analyzes RSS headlines and emits `(coin, action, confidence, reasoning)` records
- [x] ISC-9: Pump signals — coins with ≥3x normal volume are flagged with a confidence scaled by spike size
- [x] ISC-10: New listing signals — Kraken blog RSS triggers an immediate buy on listing day
- [ ] ISC-11: `STRATEGY.md` documents the three signal sources and their combination rules end to end

### Trading

- [x] ISC-12: Open orders are cancelled at the start of each cycle to free funds
- [x] ISC-13: `MAX_TRADE_AMOUNT` caps per-trade CAD spend
- [x] ISC-14: Sells are skipped for coins not currently held
- [x] ISC-15: Positions (`entry_price`, `amount_cad`) are recorded on buy and removed on sell

### Observability

- [ ] ISC-16: All trade events append one JSON object per trade to `trades.jsonl`
- [ ] ISC-17: Every Kraken API method logs its latency
- [ ] ISC-18: `scripts/daily_pnl.py` aggregates `trades.jsonl` into a daily PnL summary
- [ ] ISC-19: `latest_status.json` is written each cycle with run timestamp, balance, holdings, last decision, errors

### Quality

- [ ] ISC-20: Pytest scaffold present and `pytest --collect-only` exits 0
- [ ] ISC-21: At least one test per module in `tests/` (`test_market_matcher.py`, `test_news_fetcher.py`, `test_kraken_client.py`)
- [ ] ISC-22: GitHub Actions runs `pytest` on push; README shows the badge
- [ ] ISC-23: `kraken_client.py` has type hints on every function (mypy clean)
- [ ] ISC-24: `trader.py` has type hints on every function (mypy clean)
- [ ] ISC-25: Every function in `kraken_client.py` has a docstring

### Resilience

- [ ] ISC-26: Every Kraken API call is wrapped in `@retry` with exponential backoff
- [ ] ISC-27: A rate limiter enforces ≥1 second between Kraken API calls
- [ ] ISC-28: Drawdown circuit breaker liquidates positions on ≥15% session drawdown

### Security

- [ ] ISC-29: `SECURITY.md` documents API key storage, rotation, kill switch, network exposure, and incident response
- [ ] ISC-30: `.env.example` exists and lists every environment variable with a placeholder value

### Deploy

- [ ] ISC-31: `deploy/kraken-bot.service` matches the systemd unit running on the VPS
- [ ] ISC-32: `scripts/deploy.sh` runs tests, scp's the repo, restarts the service, and tails logs

### Anti-criteria

- [ ] ISC-33: Anti: no auto-commit cron, no GitHub-activity-inflation script, no fake-commit automation lives in this repo
- [ ] ISC-34: Anti: no secret values (`KRAKEN_API_KEY`, `KRAKEN_PRIVATE_KEY`, `ANTHROPIC_API_KEY` actual values) appear in any committed file
- [ ] ISC-35: Anti: the bot does not trade outside CAD pairs
- [ ] ISC-36: Anti: live trading never runs without `DAILY_LOSS_LIMIT` configured
- [ ] ISC-37: Anti: code that affects runtime behavior is not deployed without a local dry-run

### Antecedent

- [ ] ISC-38: Antecedent: `DAILY_ITERATIONS.md` has an open task for any unchecked ISC in this list

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

## Changelog

- 2026-05-20 **seeded** | conjectured: "A meme coin bot only needs strategy code." | refuted by: "Three commits in two months, no tests, no runbook, no observability — the surface that fails first is the engineering scaffold, not the strategy." | learned: The project's risk surface is operational and observational, not just algorithmic. | criterion now: 38 ISCs cover ops, signals, trading, observability, quality, resilience, security, deploy, anti-criteria, and antecedent — the engineering scaffold IS the ISA.

## Verification

- ISC-1: `systemctl is-active kraken-bot` returns `active` on `root@204.168.204.221` (per project memory and prior verification on Day 1 setup)
- ISC-2: `cat .gitignore` shows `.env` on line 1; `git ls-files | grep "^.env$"` returns nothing
- ISC-3: `trader.py:90` enforces `if daily_loss >= DAILY_LOSS_LIMIT: return`
- ISC-4: `trader.py:32` and `trader.py:47` enforce stop-loss / take-profit branches
- ISC-8: `market_matcher.analyze_news_for_trades` produces signal records (see `trader.py:141`)
- ISC-9: `pump_detector.find_pumping_coins` with `min_volume_multiplier=3.0` (see `trader.py:125`)
- ISC-10: `listing_monitor.check_new_listings` triggers immediate buy (see `trader.py:111`)
- ISC-12: `trader.py:74` cancels open orders at cycle start
- ISC-13: `trader.py:168` uses `MAX_TRADE_AMOUNT * confidence`
- ISC-14: `trader.py:159` skips sells for non-held coins
- ISC-15: `positions.record_buy` and `positions.remove_position` (see `trader.py:120,189`)
- (Remaining ISCs are pending — each is mapped to a `DAILY_ITERATIONS.md` task, satisfying ISC-38)
