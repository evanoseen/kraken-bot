# Daily Iterations

A curated 30-task backlog for shipping a real commit every day on this bot. Each task is sized for 10 to 30 minutes of focused work and has explicit done conditions.

## How to use this

1. Each morning, run `./scripts/daily.sh` from the repo root. It prints today's task by day index since 2026-05-19.
2. Do the task. Aim for one commit per day, descriptive message, push to `origin/main`.
3. Add a one paragraph entry to `JOURNAL.md` covering what shipped, what surprised you, what's next.
4. If today's task is blocked, skip ahead to a task in a different category and note the swap in the journal.
5. After Day 31, Day 28 expands the backlog by 10 more tasks.

**Ordering principle:** safe first (docs, tests), medium (refactors, observability), then behavior changes (features, ops/deploy). Never deploy on a busy day.

---

## Day 1: Stand up the daily iteration system
**Why:** Without a backlog and a frictionless picker, willpower is the bottleneck and the contribution graph stays empty.
**Do:** Create `DAILY_ITERATIONS.md`, `JOURNAL.md`, and `scripts/daily.sh`. Update `README.md`. Commit and push.
**Done when:** All four files exist, picker prints today's task, commit is pushed to `origin/main`, and the contribution graph shows a green square. (Shipped 2026-05-19.)

---

## Documentation (Days 2 to 8)

## Day 2: Seed a project ISA
**Why:** The PAI Algorithm treats project work as iteration on a long lived ISA. The bot needs one.
**Do:** Create `ISA.md` at the repo root with Problem, Vision, Out of Scope, Constraints, Goal, and an empty Criteria section. Use the twelve section template from PAI doctrine.
**Done when:** `ISA.md` exists at repo root, has at least the six sections named above, and frontmatter has `project: kraken-bot` and `phase: observe`.

## Day 3: Docstring every function in `kraken_client.py`
**Why:** First file a new reader opens. Docstrings double as a forcing function to spot weird method shapes.
**Do:** Add a one or two line docstring to every function in `kraken_client.py` describing args, returns, and side effects (network calls, state mutations).
**Done when:** `python3 -c "import ast, sys; m=ast.parse(open('kraken_client.py').read()); funcs=[n for n in ast.walk(m) if isinstance(n, ast.FunctionDef)]; print(all(ast.get_docstring(f) for f in funcs))"` prints `True`.

## Day 4: Write `STRATEGY.md`
**Why:** The bot uses three signals (news, pump, listing) and the strategy logic is buried in code.
**Do:** Create `STRATEGY.md` explaining each signal source, the confidence math, position sizing, and exit logic. Use diagrams if helpful.
**Done when:** `STRATEGY.md` exists, covers all three signals with at least one paragraph each, and explains the buy/sell decision flow end to end.

## Day 5: Write `OPS_RUNBOOK.md`
**Why:** The bot is live on Hetzner. Future you will forget the systemd commands.
**Do:** Create `OPS_RUNBOOK.md` with sections for: SSH access, systemd commands, log inspection, deploy procedure, rollback procedure, and "bot is misbehaving" triage steps.
**Done when:** `OPS_RUNBOOK.md` exists with at least the six sections above and concrete commands (not just descriptions).

## Day 6: Write `.env.example`
**Why:** Anyone cloning the repo (or future you on a new machine) needs to know every env var the bot reads.
**Do:** Create `.env.example` with every variable from `config.py`, sane non secret defaults, and a `#` comment per line explaining the variable.
**Done when:** `.env.example` exists, every variable in `config.py` appears in it, and no real secret values are present (placeholder strings only).

## Day 7: Add an architecture diagram to README
**Why:** Recruiters skim the README. A picture earns 10x the engagement of prose.
**Do:** Add a Mermaid diagram to `README.md` showing: news fetcher and pump detector and listing monitor feeding the trader, trader calling kraken_client, kraken_client hitting the Kraken API. Place it under a new "Architecture" section.
**Done when:** `README.md` contains a `\`\`\`mermaid` block with at least 5 nodes and 4 edges, rendered correctly when previewed on GitHub.

## Day 8: Write `SECURITY.md`
**Why:** This bot moves real money. A security threat model is overdue.
**Do:** Create `SECURITY.md` covering: API key storage, key rotation procedure, kill switch design, network exposure of the VPS, dependency vulnerability policy, and incident response steps.
**Done when:** `SECURITY.md` exists with all six topics above and at least one concrete action per topic (not just principles).

---

## Tests (Days 9 to 13)

## Day 9: Add pytest scaffold
**Why:** No tests today. The first one is the hardest. Get the rig in place.
**Do:** Add `pytest` and `pytest-mock` to `requirements.txt`. Create `tests/conftest.py` with a `kraken_dryrun` fixture that returns a mocked client. Create `tests/__init__.py`. Verify with `pytest --collect-only`.
**Done when:** `pytest --collect-only` exits 0 from the repo root and discovers the tests folder.

## Day 10: Write `tests/test_market_matcher.py`
**Why:** `market_matcher.py` has pure logic — perfect first unit test target.
**Do:** Write at least two tests: one for matching a known coin name to a Kraken ticker, one for handling an unknown coin gracefully. Use parametrize if helpful.
**Done when:** `pytest tests/test_market_matcher.py -v` shows at least two passing tests.

## Day 11: Write `tests/test_news_fetcher.py`
**Why:** RSS parsing is brittle. Pin it down with mocked feeds.
**Do:** Use `pytest-mock` to mock `feedparser.parse` and verify that `news_fetcher.fetch()` returns the right shape, skips entries with no title, and deduplicates by link.
**Done when:** `pytest tests/test_news_fetcher.py -v` shows at least three passing tests covering happy path, no title, and dedupe.

## Day 12: Write `tests/test_kraken_client.py`
**Why:** Network calls are the riskiest surface. Mock them.
**Do:** Use `requests-mock` (add to requirements) to verify that `KrakenClient.get_balance()` parses a known response shape and that an HTTP 5xx raises a sensible exception.
**Done when:** `pytest tests/test_kraken_client.py -v` shows at least two passing tests, one happy path one error path.

## Day 13: Add GitHub Actions CI
**Why:** Green check on every push beats running pytest manually.
**Do:** Create `.github/workflows/test.yml` that on push runs Python 3.11, installs requirements, runs `pytest`. Add a status badge to the top of README.
**Done when:** The workflow file exists, GitHub shows a green check on the commit that adds it, and the README badge resolves.

---

## Refactors (Days 14 to 19)

## Day 14: Replace `print()` with `logging`
**Why:** Logs in journalctl will be searchable, leveled, and timestamped properly.
**Do:** Configure the root logger in `main.py` to write to stdout at INFO with a `[%(asctime)s] %(levelname)s %(name)s: %(message)s` format. Replace every `print()` in the codebase with a module logger call.
**Done when:** `grep -rn "print(" *.py` returns zero results in the trading modules (test files exempt).

## Day 15: Type hints for `kraken_client.py`
**Why:** Type hints document intent and unlock IDE help.
**Do:** Add full type hints to every function signature in `kraken_client.py`, including return types. Use `Optional[X]` for nullable.
**Done when:** `python3 -m mypy --ignore-missing-imports kraken_client.py` returns zero errors.

## Day 16: Type hints for `trader.py`
**Why:** Trader is the most complex file. Types help future you read it.
**Do:** Add full type hints to every function signature in `trader.py`.
**Done when:** `python3 -m mypy --ignore-missing-imports trader.py` returns zero errors.

## Day 17: Extract a `Config` dataclass
**Why:** `config.py` likely returns a dict or globals. A dataclass gives type safety and explicit field names.
**Do:** Refactor `config.py` to return a frozen `@dataclass` with one field per env var. Update all callers.
**Done when:** `config.py` exports a `Config` dataclass; `from config import Config; c = Config.from_env()` works; all callers use attribute access (`c.max_trade_amount`) not dict access.

## Day 18: Add retry decorator with `tenacity`
**Why:** Kraken API returns 429s during volatility. Retries with backoff are table stakes.
**Do:** Add `tenacity` to requirements. Wrap each Kraken API method with `@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))`. Log retry attempts.
**Done when:** Every method in `kraken_client.py` that makes a network call is decorated with `@retry`, and a unit test verifies retry fires on a simulated 429.

## Day 19: Rate limiter for Kraken calls
**Why:** Kraken throttles per IP. A token bucket prevents 429 cascades.
**Do:** Add a simple rate limiter (e.g. `ratelimit` library or a manual `last_call` timestamp + sleep). Cap to 1 call per second.
**Done when:** `kraken_client.py` enforces a minimum 1 second between API calls and a test verifies the delay.

---

## Observability (Days 20 to 23)

## Day 20: Trade events as JSONL
**Why:** Every trade should be reproducible and auditable from a log file.
**Do:** Append one JSON object per trade to `trades.jsonl` with timestamp, pair, side, volume, price, order_id, signal_source. Add `trades.jsonl` to `.gitignore`.
**Done when:** A dry run trade produces a valid JSON line in `trades.jsonl` (verify with `python3 -c "import json; [json.loads(l) for l in open('trades.jsonl')]"`).

## Day 21: Heartbeat file
**Why:** "Is the bot alive?" should be answerable without SSH.
**Do:** Write `last_run.txt` with the current ISO timestamp at the end of every cycle. Add to `.gitignore`.
**Done when:** Running the bot once writes a timestamp to `last_run.txt` and the file is git ignored.

## Day 22: API latency logging
**Why:** Slow Kraken responses are the first sign of an upcoming outage.
**Do:** Wrap each Kraken API method to time `t0 = time.monotonic()`, call, then `logger.info("kraken.<method> took %.2fs", elapsed)`.
**Done when:** Every Kraken API method logs its latency on each call.

## Day 23: Daily PnL summary script
**Why:** "Did the bot make money today?" is the highest signal question.
**Do:** Write `scripts/daily_pnl.py` that reads `trades.jsonl`, aggregates by day, prints buy/sell counts, net CAD flow, and current balance fetched from Kraken.
**Done when:** `python3 scripts/daily_pnl.py` prints a table of trades and a net PnL line.

---

## Features (Days 24 to 28)

## Day 24: Kill switch file
**Why:** If the bot misbehaves, SSH plus systemctl plus typing the command takes too long. A file watch is instant.
**Do:** At the top of each cycle, check for a `KILL` file in the repo root. If present, log a warning and exit cleanly. Document in README and OPS_RUNBOOK.
**Done when:** `touch KILL` followed by next cycle causes the bot to exit with a clean log line; removing the file allows restart.

## Day 25: CLI flags for `main.py`
**Why:** Currently `main.py` always runs the full scheduler. Sometimes you want one cycle or a dry run override.
**Do:** Use `argparse` to add `--once` (run a single cycle then exit) and `--dry-run` (force DRY_RUN=true regardless of env).
**Done when:** `python3 main.py --once --dry-run` runs one cycle, never places a real order, then exits with code 0.

## Day 26: Status JSON file
**Why:** Dashboards or other scripts can poll a file faster than scraping logs.
**Do:** After each cycle, write `latest_status.json` with last_run_timestamp, balance, open_positions, last_decision, errors_this_cycle. Add to `.gitignore`.
**Done when:** `latest_status.json` exists after one cycle and contains all five fields.

## Day 27: Maximum drawdown circuit breaker
**Why:** A bug in signal logic could chew through the daily limit. A drawdown breaker is a second safety net.
**Do:** Track session_start_balance. If current_balance < session_start_balance * 0.85 (15% drawdown), liquidate all positions and exit.
**Done when:** A unit test simulating a 16% drawdown triggers a liquidation call in the trader.

## Day 28: Telegram or Discord notifications
**Why:** Mobile alerts on trade execution close the loop.
**Do:** Pick one (Telegram bot API or Discord webhook). Add `NOTIFICATION_URL` env var. Post a message on each trade with signal source, pair, side, volume, price. Also: refresh this backlog by adding 10 more tasks below.
**Done when:** A trade in dry run mode fires a real notification to the chosen channel and DAILY_ITERATIONS.md has 10 new tasks queued (Days 32 to 41).

---

## Ops & Deploy (Days 29 to 31)

## Day 29: Add a `Makefile`
**Why:** Common commands should be one word.
**Do:** Create `Makefile` with targets: `make test`, `make run`, `make dry`, `make deploy`, `make logs`, `make restart`, `make status`. Use `.PHONY` properly.
**Done when:** Running `make test` exits 0 (delegates to pytest) and `make` with no target prints a help listing of all targets.

## Day 30: Commit the systemd unit to the repo
**Why:** The unit file lives only on the server. Losing the server loses the unit.
**Do:** Save the production `kraken-bot.service` content to `deploy/kraken-bot.service` in the repo. Update OPS_RUNBOOK to reference it.
**Done when:** `deploy/kraken-bot.service` exists, matches what is on the server (`ssh root@204.168.204.221 cat /etc/systemd/system/kraken-bot.service` returns the same content), and OPS_RUNBOOK references it.

## Day 31: One command deploy script
**Why:** Ship faster, fewer mistakes.
**Do:** Write `scripts/deploy.sh` that runs: pytest, scp the repo to the VPS, ssh in to restart the service, tail 20 log lines to confirm health. Fail loudly on any step.
**Done when:** `./scripts/deploy.sh` end to end pushes a no op change to the VPS and the bot keeps running (verified via the heartbeat from Day 21).

---

## After Day 31

Day 28's task includes a directive to append Days 32 to 41 to this file. Keep the same shape: name, why, do, done when. Rotate categories so the bot keeps improving along multiple axes.

---

## Status note (added Day 55, 2026-08-01)

The Day 28 directive above was never fulfilled — the backlog stalled at Day 31 and every day since has been picked ad hoc instead of read from this file. Cross-checking `git log` against Days 26 to 31 above: Day 26 (status JSON), Day 27 (drawdown breaker), and Day 28's Telegram half all shipped close to plan, but **Day 29 (Makefile), Day 30 (commit the systemd unit), and Day 31 (deploy script) never happened** — those day numbers got reused for unrelated organic work (cooldown, health check, stale-position exit) once nobody was reading this file anymore.

Day 55 closed the Makefile gap (`Makefile` now exists with `test`/`run`/`dry`/`deploy`/`logs`/`restart`/`status`, mirroring the OPS_RUNBOOK deploy ritual). **Days 30 and 31's originals are still open** — committing `deploy/kraken-bot.service` and writing `scripts/deploy.sh` both need to diff against or reach the live VPS, which the environment doing this backlog work does not have SSH access to. Picked up below as real tasks, re-numbered to the actual day count instead of the stale 32 to 41 range (which real commits already used for other things).

## Day 56: Commit the systemd unit to the repo
**Why:** The unit file lives only on the server. Losing the server loses the unit. (Original Day 30, never done.)
**Do:** SSH in, `cat /etc/systemd/system/kraken-bot.service`, save the content to `deploy/kraken-bot.service` in the repo. Reference it from OPS_RUNBOOK.
**Done when:** `deploy/kraken-bot.service` exists, matches the live unit file byte for byte, and OPS_RUNBOOK references it.

## Day 57: One command deploy script
**Why:** `make deploy` (Day 55) still hand-waves the rsync/restart/verify steps into raw shell in the Makefile recipe. A dedicated script can fail loudly per step and get exercised on its own. (Original Day 31, never done.)
**Do:** Write `scripts/deploy.sh`: run pytest, rsync excluding `.env`/`.git`, ssh restart, poll `last_run.txt` (Day 21 heartbeat) until it advances past the pre-deploy timestamp or timeout. Point the Makefile's `deploy` target at it.
**Done when:** `./scripts/deploy.sh` end to end pushes a no-op change to the VPS, the bot keeps running, and the heartbeat file advances within the timeout.

## Day 58: Dependency vulnerability scan in CI
**Why:** `SECURITY.md` names "dependency vulnerability policy" as a topic but nothing enforces it — `requirements.txt` has never been scanned.
**Do:** Add a `pip-audit` (or `safety`) step to `.github/workflows/test.yml` that runs after the pytest step. Document the remediation process in `SECURITY.md`.
**Done when:** The CI workflow has a vuln-scan step, it runs green on the commit that adds it, and `SECURITY.md`'s dependency section links to it.

## Day 59: Trades CSV/JSONL log rotation
**Why:** Day 54 rotated `bot.log`. `trades.csv` and `trades.jsonl` (Day 20) are append-only forever too, just slower growing since a trade is rarer than a log line.
**Do:** Add a `scripts/archive_trades.py` that moves `trades.csv`/`trades.jsonl` entries older than N days into a dated archive file, or rotates by size like Day 54. Wire a monthly cron suggestion into OPS_RUNBOOK.
**Done when:** Running the script against a synthetic old trades file splits it into current + archived, and both remain valid CSV/JSONL.

## Day 60: `scripts/daily_pnl.py` gains a `--since`/`--until` range
**Why:** Day 23's script only aggregates by calendar day with no filtering — answering "how did last week go" means eyeballing a long table.
**Do:** Add `--since YYYY-MM-DD` and `--until YYYY-MM-DD` flags that filter the aggregation window before printing.
**Done when:** `python3 scripts/daily_pnl.py --since 2026-07-25 --until 2026-07-31` prints only that week's rows and a matching subtotal.

## Day 61: Alert when the heartbeat goes stale
**Why:** Day 52 added a Telegram alert on *graceful* shutdown, but a hard crash or a hung process (OOM, deadlock) leaves no signal — `last_run.txt` (Day 21) just stops advancing silently.
**Do:** Write `scripts/check_heartbeat.py`: read `last_run.txt`, and if it's older than `2 * RUN_INTERVAL_MINUTES`, send a Telegram alert via `notifier`. Add an OPS_RUNBOOK section on running it from an external cron (not on the VPS itself, or a wedged VPS can't alert on itself).
**Done when:** A synthetic stale heartbeat file (timestamp older than the threshold) triggers a Telegram call in a unit test; a fresh one does not.

## Day 62: Position sizing scaled by confidence
**Why:** Every trade currently uses a flat amount up to `MAX_TRADE_AMOUNT` regardless of whether the signal confidence was 0.80 or 0.99 — no distinction between a marginal and a strong signal.
**Do:** In `trader.py`, scale the trade size between `MIN_TRADE_AMOUNT` and `MAX_TRADE_AMOUNT` linearly (or another documented curve) based on `confidence`. Document the formula in `STRATEGY.md`.
**Done when:** A unit test confirms a 0.99-confidence signal sizes a larger trade than an 0.81-confidence signal, both within the configured min/max bounds.

## Day 63: `.env.example` audit against `config.py`
**Why:** Day 6 wrote `.env.example` once; a dozen `Config` fields have been added since (Day 53's fix confirmed the drift on the test side — the env file itself has never been re-checked).
**Do:** Diff every `Config.from_env()` os.getenv() call against `.env.example`'s entries. Add any missing var with a comment; remove any that no longer exist.
**Done when:** A small script or one-liner confirms every env var `config.py` reads appears in `.env.example`, and vice versa.

## Day 64: README badge + status section refresh
**Why:** Day 13 added a CI badge; day-to-day feature growth since (blacklist, cooldown, headline cache, geo-block filter, shutdown alerts, log rotation) has never been reflected back into the README's feature list.
**Do:** Regenerate the README "Features" section from the current module set. Confirm the CI badge still resolves and the Day 7 Mermaid diagram still matches the real call graph.
**Done when:** README's feature list has no gaps against `ls *.py`'s module docstrings, and the Mermaid diagram renders correctly on GitHub.

## Day 65: `JOURNAL.md` catch-up entry
**Why:** `JOURNAL.md` (Day 1's ask: "one paragraph per day covering what shipped, what surprised you, what's next") has a real entry for every day only through Day 25 — thirty-plus days of shipped work have no journal record.
**Do:** Write one retrospective entry summarizing Days 26 to 65 as a block: what categories of work happened (features, ops, test-debt), the biggest surprise (the backlog itself going unread for a month), and what's next after Day 65.
**Done when:** `JOURNAL.md` has a dated entry covering the Day 26-65 gap and resumes normal one-entry-per-day going forward.

---

## Status note (added Day 66, 2026-08-14)

This backlog hit its ceiling again — same pattern as the Day 55 status note above, just caught after 10 days instead of a month, because Day 65's journal entry flagged it as the very next task instead of it silently going unread. Re-surveyed the codebase before writing new entries rather than guessing: found two small real bugs fixed directly today (`.gitignore` excluded `latest_status.json`, a filename from the original Day 26 plan, instead of `status.json`, what Day 45 actually shipped — meaning the real runtime status file was never excluded from git; `STRATEGY.md`'s "Known structural weaknesses" section was 100% stale, listing seven things that all shipped between Days 18 and 53). `STRATEGY.md` has the re-audited, currently-true version of that list — Days 67-76 below are pulled directly from it, not invented.

## Day 67: Docstrings for the remaining modules
**Why:** Day 3 covered `kraken_client.py` only. `heartbeat.py`, `kill_switch.py`, `listing_monitor.py`, `market_matcher.py`, `news_fetcher.py`, `positions.py`, `pump_detector.py`, and `trader.py` still have no module docstring — confirmed via Day 64's docstring audit.
**Do:** Add a module-level docstring to each file listed above, matching the style already used elsewhere (one-line summary, Day-number reference if it shipped as a named feature, brief usage note where non-obvious).
**Done when:** `python3 -c "import ast; [print(f, bool(ast.get_docstring(ast.parse(open(f).read())))) for f in [...]]"` prints `True` for every file in the list.

## Day 68: Type hints + mypy clean beyond kraken_client.py and trader.py
**Why:** Days 15-16 only covered two files. Day 66 found this the hard way: a mypy version bump stopped honoring `mypy.ini`'s `follow_imports = silent`, which turned two *latent* transitive-import issues into two *failing* tests (`config.py`'s `Optional[str]`-into-`float()` pattern, and a missing `types-requests` stub for `notifier.py`) — both fixed same-day to get back to green, but `status.py` and `blacklist.py` are still unaudited and have no type hints at all.
**Do:** Add full type hints to `status.py` and `blacklist.py` (config.py and notifier.py's known issues are already fixed as of Day 66). Fix whatever else mypy surfaces now that `follow_imports=silent` can't be relied on to hide it.
**Done when:** `python3 -m mypy --ignore-missing-imports config.py notifier.py status.py blacklist.py` returns zero errors.

## Day 69: Trailing stop-loss exit option
**Why:** The strategy's biggest asymmetry, flagged in the Day 4 journal entry and still true today — three independent catalyst-driven entry signals, but exit is just two fixed percentages off the entry price. Nothing locks in gains as a position runs up before reversing.
**Do:** Add a `TRAILING_STOP_PCT` config option (optional, defaults to disabled = current behavior). When set, track the position's peak price since entry and exit if price falls `TRAILING_STOP_PCT` off that peak, instead of only checking against the fixed entry-price stop-loss. Document the interaction with `STOP_LOSS_PCT`/`TAKE_PROFIT_PCT` in `STRATEGY.md`.
**Done when:** A unit test simulating a position that runs up 20% then drops 8% triggers a trailing-stop exit at the configured trail percentage, while an equivalent position that never ran up does not exit early.

## Day 70: Nitter failover unit test
**Why:** `news_fetcher.py` fails over across three Nitter instances (`nitter.poast.org`, `nitter.privacydev.net`, `nitter.1d4.us`), but nothing exercises that path — a partial outage's actual behavior is unverified.
**Do:** Mock the first one or two instances to fail (timeout, 5xx, connection error) and assert the fetcher falls through to the next, and that a headline set is still returned. Cover the all-three-down case too (should degrade to empty, not crash).
**Done when:** `pytest tests/test_news_fetcher.py -v` shows passing tests for single-instance failure, cascading failure, and all-instances-down, each asserting the expected fallback behavior.

## Day 71: Pin requirements.txt upper bounds
**Why:** Every dependency is `>=` with no ceiling, so a fresh install can silently pull a breaking major-version bump. `SECURITY.md`'s policy says to read the changelog before any upgrade, but nothing enforces that on first install — the unpin itself is the gap, not the absence of a policy.
**Do:** Add an upper-bound pin to each entry in `requirements.txt` (e.g. `requests>=2.31.0,<3.0.0`), one major version above the currently-installed version. Document the bump procedure (bump one dep, run `make test`, commit) in `SECURITY.md` section 5.
**Done when:** Every line in `requirements.txt` has both a lower and upper bound, `make test` still passes, and CI is green on the commit that adds the pins.

## Day 72: Test coverage measurement
**Why:** 300+ tests exist with zero visibility into which lines or branches they actually exercise. A green suite doesn't mean full coverage — it means the tests that exist pass.
**Do:** Add `pytest-cov` to `requirements.txt`. Wire `--cov=. --cov-report=term-missing` into `make test` (or a separate `make coverage` target). Report the overall percentage and identify the two or three files with the lowest coverage.
**Done when:** `make coverage` (or equivalent) prints a per-file coverage table and an overall percentage, committed as a comment or note in this backlog entry once run.

**Result (run 2026-08-21):** 83% overall (1290 statements, 214 missed), 314 tests, `tests/`/`venv/`/site-packages excluded via `.coveragerc`. Three lowest: **`pump_detector.py` at 8%** and **`listing_monitor.py` at 28%** — both have zero direct unit tests at all (no `test_pump_detector.py` or `test_listing_monitor.py` exists; every mention of `find_pumping_coins`/`check_new_listings` elsewhere in the suite mocks them out entirely, never calling the real logic) — and **`positions.py` at 57%** (mostly `load_positions`'s exception-handling branches and `log_trade`'s CSV-write-failure path). `kraken_client.py` (75%) and `trader.py` (82%) are next, mostly untested error/edge branches rather than whole untested functions. Queued the two zero-coverage modules as Day 77.

## Day 73: Config validation at load time
**Why:** `Config.from_env()` casts every env var to its type but never checks whether the *values* make sense — `MIN_TRADE_AMOUNT > MAX_TRADE_AMOUNT`, a negative `STOP_LOSS_PCT`, `MIN_CONFIDENCE` outside `[0, 1]` would all load silently and fail confusingly downstream instead of failing loud at startup, where `health.py` already checks for *missing* vars but not nonsensical ones.
**Do:** Add a `validate()` method (or inline checks in `from_env()`) that raises a clear `ValueError` for out-of-range or contradictory values. Call it from `health.run_checks()` alongside the existing missing-var check.
**Done when:** A unit test with `MIN_TRADE_AMOUNT` set above `MAX_TRADE_AMOUNT` raises a clear error at config load time instead of silently producing a broken `size_position()` curve.

## Day 74: Positions reconciliation check
**Why:** `SECURITY.md`'s incident-response runbook manually compares `positions.json` to the Kraken ledger *during* an incident — there's no day-to-day check that catches drift (a manual trade, a partial fill, state corruption) before it escalates into one.
**Do:** Write `scripts/reconcile_positions.py`: fetch live Kraken holdings, compare against `positions.json`, and report (or Telegram-alert via `notifier`, matching Day 61's pattern) any coin held on one side but not the other. Suggest a daily cron in `OPS_RUNBOOK.md`.
**Done when:** Run against a synthetic mismatch (a coin in `positions.json` not in the mocked Kraken holdings, and vice versa) and confirm both directions are reported.

## Day 75: `SECURITY.md` re-audit for stale "planned" language
**Why:** Day 58 fixed the dependency-policy section and the kill-switch section's stale "planned, Day 24" wording, but didn't do a full pass — the same drift pattern that hit `STRATEGY.md` (fixed Day 66) and the README (fixed Day 64) may still be sitting in the other five sections.
**Do:** Read `SECURITY.md` top to bottom against the current codebase. Fix any remaining "planned"/"will"/future-tense language describing something that has already shipped.
**Done when:** A grep for `planned|will add|not yet` across `SECURITY.md` returns zero matches that describe already-shipped functionality.

## Day 76: Dependabot config for automated dependency PRs
**Why:** Day 58's `pip-audit` finds known vulnerabilities but doesn't propose the fix; Day 71 pins upper bounds but someone still has to notice when a new minor/patch version ships. Automating the PR closes the loop between "audit found something" and "someone bumps it."
**Do:** Add `.github/dependabot.yml` configured for the `pip` ecosystem, weekly schedule, grouped minor/patch updates. Confirm it targets `requirements.txt`.
**Done when:** `.github/dependabot.yml` exists, is valid YAML, and GitHub's repo settings show Dependabot as active for this repo (Insights → Dependency graph → Dependabot).

## Day 77: Unit tests for pump_detector.py and listing_monitor.py
**Why:** Day 72's coverage run found these two core signal-source modules at 8% and 28% — not "needs more edge cases," genuinely zero direct unit tests. Every other test that touches `find_pumping_coins`/`check_new_listings` mocks them out completely, so their actual volume-spike math, `IGNORE_COINS` filtering, RSS title parsing, and `WATCHLIST` matching have never been exercised by anything but production traffic.
**Do:** Write `tests/test_pump_detector.py`: mock the Kraken client's `query_public` responses to cover the spike-ratio math, the $5M daily-volume ceiling, `IGNORE_COINS` filtering, and the zero-division/malformed-ticker guards. Write `tests/test_listing_monitor.py`: mock `feedparser.parse` to cover a watchlist match, a non-watchlist listing (logged but not bought), an already-seen entry being skipped, and the `seen_listings.json` persistence round-trip.
**Done when:** `make coverage` shows both files above 80%, and the full suite still passes.
