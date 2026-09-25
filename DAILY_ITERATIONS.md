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

**Update (Day 77, 2026-08-26):** `pump_detector.py` now 98%, `listing_monitor.py` 100%. Overall coverage 83% → 90%, 407 tests. Writing real tests for `pump_detector.py` surfaced a genuine bug the mocked-everywhere-else tests had never exercised: its exception guard caught `ValueError, KeyError, ZeroDivisionError` but not `IndexError` — a ticker response with a short `v`/`l`/`h` list (plausible for a newly-listed or degenerate pair) would crash the *entire* scan instead of just skipping that one coin. Fixed by adding `IndexError` to the guard. `positions.py` (57%) is the new lowest-coverage file, not yet addressed.

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

## Day 78: Unit tests for positions.py
**Why:** Day 77's coverage re-run flagged `positions.py` at 57% as the new lowest — same pattern as `pump_detector.py`/`listing_monitor.py` before it: no `test_positions.py` exists at all. Every call site elsewhere mocks `record_buy`/`remove_position`/`get_position`/`log_trade` directly rather than exercising the real read/write/exception-handling logic.
**Do:** Write `tests/test_positions.py` covering `load_positions` (missing file, malformed JSON), `save_positions`/`record_buy`/`remove_position`/`update_peak_price` (real file round-trips, sandboxed via `monkeypatch.chdir(tmp_path)`), and `log_trade`'s CSV + JSONL writes including the write-failure exception branches and the action-string-without-underscore fallback (`side, signal_source = action, "unknown"`).
**Done when:** `make coverage` shows `positions.py` above 85%, and the full suite still passes.

---

## Status note (added Day 79, 2026-08-29)

Backlog ran dry three times in four days (76→77, 77→78, 78→79) — the single-entry-at-a-time pattern from Days 77/78 isn't sustainable. Also found the biggest piece of drift yet while surveying for what to add: `ISA.md`, the project's own declared "system of record" ("iteration on the bot is iteration on this file"), had `updated: 2026-05-20` in its frontmatter — untouched since Day 2, through 76 subsequent days of shipped work. 34 of its 38 criteria were still marked unchecked despite the corresponding features (kill switch, heartbeat, JSONL trades, drawdown breaker, deploy script, and more) having shipped and been in daily use for weeks. Fixed as today's actual task — see `ISA.md`'s Day 79 Changelog entry for the full account. Days 80-85 below come out of that same pass, not guessed.

## Day 80: kraken_client.py coverage improvement
**Why:** Day 77's coverage survey named `kraken_client.py` (75%) as the next-lowest file after the two zero-coverage modules got fixed. Unlike those, it already has a test file (`test_kraken_client.py`, since Day 15) — the gap is specific missing branches, not the whole module.
**Do:** Read the current `make coverage` missing-lines list for `kraken_client.py` and add tests for whichever error/edge branches across `get_balance`, `get_holdings`, `get_tradable_coins`, `get_price`, and `place_order` are uncovered — likely Kraken error-response handling and malformed-response guards, given the pattern from Days 77-78.
**Done when:** `make coverage` shows `kraken_client.py` above 90%, and the full suite still passes.

## Day 81: trader.py coverage improvement
**Why:** The largest file in the codebase (288 statements) at 82% coverage — the last of the three files Day 72's original survey flagged, after `pump_detector.py`, `listing_monitor.py`, and `positions.py` were each brought above 90%+ on Days 77-78.
**Do:** Read the current `make coverage` missing-lines list for `trader.py` and add tests for whichever branches in `run_trading_cycle`/`check_exit_conditions` are uncovered — likely rarer exit paths (specific error-response shapes, guard clauses that rarely fire in the existing mocked-cycle tests).
**Done when:** `make coverage` shows `trader.py` above 90%, and the full suite still passes.

## Day 82: README.md re-audit
**Why:** Last regenerated Day 64. Since then: trailing stop (69), config validation (73), positions reconciliation (74), coverage tooling (72), Dependabot (76), and direct test coverage for three previously-untested modules (77, 78) have all shipped without the README's Features list or Tech Stack section being touched — the exact drift pattern Day 64 fixed the first time.
**Do:** Regenerate the Features section against the current module set and `DAILY_ITERATIONS.md`. Confirm the CI badge still resolves and the Mermaid diagram still matches the real call graph (actually verify rendering this time if a working browser tool is available — Day 64 couldn't).
**Done when:** README's feature list has no gaps against the current shipped-features list, and either the diagram is visually confirmed rendering or the verification gap is explicitly noted (not silently skipped).

## Day 83: CI coverage regression guard
**Why:** `make coverage` (Day 72) is a manual, local-only command. Nothing stops overall coverage from silently dropping in a future PR the way `.env.example`, the README, and `STRATEGY.md` all silently drifted before something forced a permanent check (Days 63, 64, 66's lesson, generalized).
**Do:** Add `--cov-fail-under=90` (or the current overall percentage, whichever is lower risk) to the `pip-audit`/pytest CI step in `.github/workflows/test.yml`, or a dedicated coverage job. Document the threshold-bump procedure (raise it, don't lower it, when coverage genuinely improves) in `CLAUDE.md`-equivalent project docs.
**Done when:** A CI run against a synthetic coverage drop (temporarily skip a test file) fails the build; the real current state passes.

## Day 84: JOURNAL.md catch-up for Days 66-79
**Why:** Day 65 already fixed this exact gap once (Days 26-54, 58-64 had no journal entries). It's back: Days 66-79 shipped with thorough commit messages but no `JOURNAL.md` paragraphs, same as before. Worth naming honestly rather than re-discovering silently: the one-entry-per-day discipline didn't survive contact with 14 more days of momentum, same as the first time.
**Do:** Write one retrospective block entry covering Days 66-79, grouped by category (same shape as Day 65's). Name the repeat explicitly as the "surprised by" finding — that's the actually useful signal, not a list of what shipped (commit messages already have that).
**Done when:** `JOURNAL.md` has a dated entry covering the Day 66-79 gap.

**Result (2026-09-07, backfilled 2026-09-19):** Shipped on time (commit `3329047`) — the "## Days 66-83 catch-up, 2026-09-07" entry in `JOURNAL.md` covers the full gap, grouped by category (meta/backlog maintenance, test coverage sweep, risk/safety features, ops/security/dependency hygiene) rather than 18 one-line day summaries, and names the repeat itself (this is the second time the one-entry-per-day discipline lapsed, after Day 65) as the actual finding. Docs-only change, 466 tests unaffected at the time. This Result paragraph itself was never appended when the day shipped — found and backfilled during the Day 91 sweep below, which is the same "shipped but undocumented" gap this day's own task was about, just one level up (hitting this tracking file instead of `JOURNAL.md`).

## Day 85: ISA v2 — define ISCs for Days 18-79 features
**Why:** Day 79's ISA re-audit deliberately scoped down to checking the original 38 ISCs against reality, not adding new ones for everything shipped since (trailing stop, confidence-scaled sizing, config validation, positions reconciliation, coverage tooling, Dependabot, blacklist/cooldown/headline-cache, and more) — see `ISA.md`'s Day 79 Decisions entry for why that was deferred rather than done same-day.
**Do:** Draft a second wave of ISCs (ISC-39 onward) covering the major features that shipped after the original 38 were seeded. Prioritize risk-relevant ones (trailing stop, config validation, reconciliation) over cosmetic ones. Update the Features and Test Strategy tables to match.
**Done when:** `ISA.md` has ISC-39+ covering at least the six features named above, each with a Test Strategy row and a Verification entry.

**Result (2026-09-09, backfilled 2026-09-19):** Shipped on time (commit `2059d46`) — added ISC-39 through ISC-44 (confidence-scaled sizing, trailing stop, config validation, positions reconciliation, coverage enforcement, Dependabot), each pre-checked with a Test Strategy row (lines 163-168) and a Verification entry citing the actual test file rather than just the implementation (lines 252-257), since all six already had dedicated tests the day they originally shipped. Deliberately scoped to just those six — `blacklist.py`/`cooldown.py`/`headline_cache.py` and full Days-18-79 exhaustiveness were explicitly left out, documented as a scope decision in ISA.md's Decisions log rather than a silent gap. Docs-only, 466 tests unaffected. Same backfill note as Day 84: this Result paragraph was never appended at the time — found and fixed during the Day 91 sweep below.

## Day 86: review the 5 open Dependabot PRs
**Why:** Dependabot (Day 76) had been dutifully opening PRs since 2026-08-25 — over two weeks — and nobody had reviewed a single one. A mechanism that opens PRs nobody looks at isn't actually closing the loop it was built for.
**Do:** Review and merge each of the 5 open PRs individually, verifying locally after each (per SECURITY.md's one-dependency-per-commit bump procedure), not as a batch.
**Done when:** All 5 PRs are either merged (verified) or explicitly closed with a documented reason.

**Result (2026-09-11):** Merged 3 safe patch/minor bumps (pytest-mock, schedule, feedparser). The feedparser merge broke `pip install` on this actual Python 3.9.6 dev environment — 6.0.13+ requires Python >=3.10, which CI's Python-3.11 runner masked completely. Fixed forward by reverting just the floor bump. Investigating further found `pytest` 9.x and `anthropic` 1.x hit the identical Python >=3.10 wall — not a one-off bad bump, a pattern across three separate upstream packages. Closed both PRs with comments explaining why, documented the finding in SECURITY.md's bump procedure, and left the project's actual Python floor (3.8+ per the README) unchanged rather than let it get silently raised as a side effect of a routine dependency review.

## Day 87: decide whether to raise the project's Python floor to 3.10+
**Why:** Day 86 found that `feedparser`, `pytest`, and `anthropic` have all dropped support for Python <3.10 in their current major releases. The project's stated floor (README: "Python 3.8+") is now blocking three routine dependency updates, and more upstream packages will likely follow the same trend over time.
**Do:** Decide deliberately — check what Python version the production VPS actually runs (needs VPS access, same blocker as Day 56), weigh the cost of a floor bump (any deploy-environment changes needed) against continuing to pin below these majors indefinitely. If raising the floor, update README/OPS_RUNBOOK/CI's `python-version`, and only then revisit the closed pytest/anthropic PRs — reading anthropic's actual 1.x migration guide before merging that one, not just trusting a mocked test suite.
**Done when:** Either the floor is deliberately raised (with README/CI updated to match) or deliberately kept at 3.8+ with the reasoning recorded — not left ambiguous.

**Result (2026-09-12):** Raised the floor to Python 3.10+. Live SSH to the VPS is still blocked (same `Permission denied` as every prior attempt, including Day 56), but `OPS_RUNBOOK.md` already documents the server as a stock Hetzner Ubuntu 24.04 image — and Ubuntu 24.04 ships Python 3.12 by default, a fact of the documented OS release, not something that needs a live login to confirm. CI already runs 3.11. Rather than take that on faith, built a real Python 3.11 venv locally, restored `feedparser` to Dependabot's originally-proposed `>=6.0.14` (the exact bump Day 86 had to revert), and ran the full suite plus coverage gate under it: 466 passed, 98.06% coverage. Updated README, `OPS_RUNBOOK.md`, `ISA.md`'s Constraints and Decisions, and `SECURITY.md`'s Day 86 note (its "README still promises 3.8" line was now stale). CI's `python-version: "3.11"` already satisfied the new floor — no change needed there. Deliberately did not reopen or merge the closed pytest 9.x / anthropic 1.x PRs today — see Day 89/90.

## Day 88: document a Dependabot PR review cadence in OPS_RUNBOOK.md
**Why:** The root cause of Day 86's 2+ week backlog wasn't that Dependabot failed — it's that nothing said when or how often to look. The same gap that hit every "living document" in this project (README, STRATEGY.md, SECURITY.md, ISA.md) before a scheduled audit was added.
**Do:** Add a short section to `OPS_RUNBOOK.md` (or extend an existing ops-cadence section) naming a concrete review interval for open Dependabot PRs, and the checklist from SECURITY.md's Day 86 update (check Python-floor compatibility, check mock-coverage depth for major bumps) as the thing to actually do during that review.
**Done when:** `OPS_RUNBOOK.md` names a specific cadence and references the Day 86 checklist.

**Result (2026-09-14):** Added `OPS_RUNBOOK.md` section 10, "Maintenance cadence" — weekly review of open Dependabot PRs, one dependency per commit, with the Day 86 checklist (Python-floor `pip download` check, mock-coverage-depth check for major bumps, decline-not-force-through if floor-blocked) spelled out inline. Timely: 5 new Dependabot PRs opened today (krakenex, anthropic 1.5.0, types-requests, python-dotenv, pytest-cov) — left them for the newly-documented weekly cadence to pick up rather than reviewing them in the same sitting as writing the policy; the anthropic one is Day 90's job specifically (needs the real migration-guide read, not a rushed same-day merge).

## Day 89: reopen and merge the pytest 9.x bump
**Why:** Day 87 raised the project's Python floor to 3.10+, which removes the only reason the pytest 9.x PR (#1) was closed rather than merged. It's still a major-version bump and deserves its own scoped review, not a same-day bundle with the floor change.
**Do:** Reopen the bump (`pytest>=9.0.0,<10.0.0` in `requirements.txt`), read pytest 9's actual changelog/migration notes for breaking changes relevant to this repo's test suite (fixture behavior, collection changes, deprecated APIs in use), then verify locally per SECURITY.md's bump procedure before committing.
**Done when:** `pytest` is bumped to 9.x, the full suite and coverage gate pass locally and in CI, and the commit message notes what the migration-notes read surfaced (or that nothing relevant applied).

**Result (2026-09-15):** Bumped `pytest>=9.0.0,<10.0.0` (resolves to 9.1.1, same version PR #1 proposed). Read pytest 9's actual changelog/deprecations page before touching the pin: dropped Python <3.8 support (moot, already at 3.10+ floor per Day 87), old-style `yield`-based generator tests now error, removed already-deprecated APIs (positional Node construction, `py.path.local` leftovers, private-module imports, `config.inicfg`), and class-scoped fixtures defined as instance methods are newly deprecated. Grepped the repo for each: no `yield` statements inside test functions (one false-positive hit on a function *named* `..._yields_exactly_one_coin`, no actual yield in its body), no `py.path.local`, no `_pytest.` internal imports, no `inicfg` usage, no fixtures defined as class instance methods (all module-level `@pytest.fixture` functions). None applied. Verified locally: 466 passed, 98.06% coverage, `pip check` clean, no deprecation warnings under `-W error::DeprecationWarning`. Committed directly to `main` rather than merging PR #1's stale branch (same git-safety practice as Day 86 — the PR's branch is 3 weeks old); closed PR #1 with a comment pointing to the commit.

## Day 90: reopen and merge the anthropic 1.x bump, after reading the real migration guide
**Why:** Day 87 raised the Python floor, which removes the only reason the anthropic 1.x PR (#3) was closed. This one carries more real risk than pytest — `tests/test_market_matcher.py` mocks `client.messages` directly, so a green suite after the bump proves the mock still works, not that the real 1.x API surface matches what this bot calls.
**Do:** Read anthropic's actual 1.x migration guide before touching the pin. Identify every call site this bot makes against the SDK (`market_matcher.py` and anywhere else it's imported), check each against the migration guide for signature/behavior changes, update the mocks in `tests/test_market_matcher.py` to match the real 1.x client shape if it changed, then bump `anthropic>=1.0.0,<2.0.0` in `requirements.txt` and verify per SECURITY.md's bump procedure.
**Done when:** `anthropic` is bumped to 1.x, the mocked tests are updated to reflect the real 1.x client surface (not just left passing against a stale mock), and a dry-run trade cycle against the live API confirms the news-signal call path still works end to end.

**Result (2026-09-18):** Read the SDK's actual MIGRATION.md before touching anything: v1.0.0's breaking changes are the httpx→httpx2 swap (only matters if you pass a custom `httpx.Client`, which this repo doesn't), removed `temperature`/`top_p`/`top_k` positional args on `messages.create()` (not used here — no sampling params are passed), and `output_format=`/`output_config=` changes (not used here — no structured-output helpers). The `.content[0].text` access pattern `market_matcher.py` and the test mock both rely on is untouched — that's the *raw HTTP response* `.text()`/`.read()` methods becoming async-aware, a different object than the parsed `Message.content` list. So `tests/test_market_matcher.py`'s `MagicMock`-shaped-like-`Message` fixture needed no changes; verified by inspection, not just a green run. Bumped `anthropic>=1.0.0,<2.0.0` in `requirements.txt`, installed 1.7.0 into the venv, full suite: 466 passed, 98% coverage, coverage gate held. Then went beyond the mocked suite: called `market_matcher.analyze_news_for_trades()` directly against the real API with real fetched headlines and the real 666-coin tradable list — got back 6 well-formed signals (AI, APT, AAVE, ARB, ADA, ATOM, all buy, 0.65-0.68 confidence), parsed cleanly, no exceptions. Also ran `main.py --once --dry-run` for the full-cycle smoke test, but the live Kraken balance ($0.01 CAD) short-circuits the trader before it reaches the news-analysis step — so that alone would *not* have proven the anthropic 1.x path works; the direct call above is what actually closes this task's done-when bar. One real finding along the way: `python3 -m mypy market_matcher.py` (this file was never in the Day 15/16/67/68 mypy-clean set, so this wasn't a regression, just newly checked) failed on `message.content[0].text` — 1.x's `ContentBlock` union grew to ~10 types (`ToolUseBlock`, `ThinkingBlock`, etc.) that don't have `.text`. Runtime was already safe (the existing `except Exception` would catch the resulting `AttributeError`), but added an explicit `isinstance(block, anthropic.types.TextBlock)` guard with a logged rejection instead of relying on the catch-all, updated the test fixture to build a real `TextBlock` instead of a bare `MagicMock`, and added a test for the non-text-block path. Final state: 467 tests passed, 98% overall coverage (market_matcher.py itself 100%), mypy clean on the file.

---

## Status note (added Day 91, 2026-09-19)

Reading top to bottom to find the next unnumbered task surfaced a new instance of this project's own recurring drift pattern — except this time it hit `DAILY_ITERATIONS.md` itself, the file that's supposed to be the record of what's done. Days 84 and 85 were both fully shipped on schedule (commits `3329047` and `2059d46`, 2026-09-07 and 2026-09-09) and both satisfy their own Done-when bar — confirmed by re-reading `JOURNAL.md`'s Days-66-83 catch-up entry for 84, and `ISA.md`'s ISC-39..44 plus its Day 85 Decisions-log entry for 85 — but neither ever got a `**Result:**` paragraph appended here. `JOURNAL.md`'s own Day 90 entry pointed to Day 85 as "still the oldest open item... should be next," which was itself stale: Day 85 had already been done for nine days by the time that line was written. Backfilled both Result paragraphs above rather than silently re-doing already-shipped work or silently skipping past the gap.

While in there, went looking for what real work was actually next and found one: Day 90's `anthropic` 1.x mypy fix (the `isinstance(block, anthropic.types.TextBlock)` guard) never got the matching regression-lock test that every other file on this project has received the same day its mypy-clean state was reached (`kraken_client.py` Day 15, `trader.py` Day 16, `config.py`/`notifier.py`/`status.py`/`blacklist.py` Day 68). A future edit to `market_matcher.py` could silently reintroduce that exact bug class with nothing in CI to catch it. Fixed today as this status note's actual shipped work — see `tests/test_market_matcher_types.py`, mirroring the existing lock-test shape exactly.

A quick mypy sweep of every `.py` file in the repo (all 23 currently clean) found no other file with an *unfixed* type error, but confirmed 16 more files still have no permanent lock test at all (`coin_trade_counter.py`, `cooldown.py`, `cycle_timer.py`, `headline_cache.py`, `health.py`, `heartbeat.py`, `kill_switch.py`, `listing_monitor.py`, `main.py`, `news_fetcher.py`, `portfolio.py`, `positions.py`, `pump_detector.py`, `retry.py`, `signals.py`, `trade_logger.py`) — clean today, but so was `market_matcher.py` until a routine dependency bump touched it. Queued as Day 92 below rather than doing all 16 in the same sitting as everything else today. Days 93-94 come from a real, verified pass over `STRATEGY.md`'s "Known structural weaknesses" list (still accurate as of Day 66, one open item) and the CI coverage gate (`--cov-fail-under=95`, unmoved since Day 83 despite coverage sitting at a stable 98% for ten days since — Day 83's own text says to raise it when that happens, not leave it).

## Day 92: lock the remaining 16 modules' mypy-clean state
**Why:** `market_matcher.py` (Day 90/91) is the fourth time this project has discovered a file was mypy-clean with nothing pinning it there — after `kraken_client.py`, `trader.py`, and the Day 68 four-file batch. 16 more modules (`coin_trade_counter.py`, `cooldown.py`, `cycle_timer.py`, `headline_cache.py`, `health.py`, `heartbeat.py`, `kill_switch.py`, `listing_monitor.py`, `main.py`, `news_fetcher.py`, `portfolio.py`, `positions.py`, `pump_detector.py`, `retry.py`, `signals.py`, `trade_logger.py`) are clean today (verified Day 91) but unlocked.
**Do:** Write `tests/test_remaining_modules_types.py` covering all 16 files in one mypy invocation plus the AST full-annotation audit, mirroring `tests/test_config_notifier_status_blacklist_types.py`'s multi-file shape.
**Done when:** `python3 -m mypy --ignore-missing-imports <all 16 files>` returns zero errors inside the test, the AST audit passes for all 16, and the full suite still passes.

**Result (2026-09-20):** Shipped `tests/test_remaining_modules_types.py`, mirroring `test_config_notifier_status_blacklist_types.py`'s shape exactly (one mypy subprocess invocation across all 16 files, plus the same AST full-annotation audit function). Ran the mypy sweep first and confirmed Day 91's claim: all 16 files were genuinely mypy-clean already. But writing the AST audit half of the test (the part Day 91's status note didn't separately check) surfaced a real gap between "mypy clean" and "fully annotated" — the same distinction Day 68 ran into with status.py/blacklist.py. Six functions across five files were mypy-clean via inferred/untyped-`Any` parameters but had no explicit annotation: `health.py`'s `_check_env`/`_log_banner`/`run_checks` all took a bare `cfg` (now typed `Config`, imported from `config.py`); `listing_monitor.py`'s `save_seen` had no return annotation (added `-> None`); `positions.py`'s `save_positions`/`record_buy`/`remove_position` were the same gap (added `-> None` to all three, matching the already-annotated `update_peak_price` next to them); `pump_detector.py`'s `find_pumping_coins` took a bare `client` (now typed `krakenex.API`, matching `kraken_client.py`'s usage); and `portfolio.py`'s `compute_value` took a bare `get_price_fn` default-`None` callable parameter. That last one needed more than a type annotation to actually pass mypy once typed as `Optional[Callable[[object, str], Optional[float]]]` — the existing pattern of reassigning the parameter itself inside `if get_price_fn is None:` via a local import (with a `# type: ignore[assignment]` papering over it) left mypy unable to narrow away the `None` branch after the `if`, so it flagged the later call as `"None" not callable`. Fixed by introducing a separately-typed `resolver` local instead of reassigning the parameter, which mypy narrows correctly with no ignore comment needed. Verified with the CI-equivalent local run: `pytest -v --cov=. --cov-report=term-missing --cov-fail-under=95` → 471 passed (469 + this file's 2 new tests), 98.14% coverage, gate held. `pip check` clean. Installed mypy 1.19.1 into a fresh Python 3.11 venv for this (same approach as Day 87) since the sandboxed dev environment's system Python has no mypy; CI already runs `mypy` implicitly via this new test file rather than as a separate workflow step, same as every prior `*_types.py` lock test in this project.

## Day 93: signal-driven exit on a stale buy thesis
**Why:** `STRATEGY.md`'s "Known structural weaknesses" section (re-audited Day 66, still accurate) names this as the one real open gap: a held position exits only on stop-loss/take-profit/trailing-stop/max-age — nothing re-evaluates whether the original news/pump catalyst that triggered the buy is still valid. A signal-driven *sell* can still close a position, but nothing proactively checks if the buy thesis has quietly expired.
**Do:** In `trader.py`'s exit-check path, add a check that re-runs (or reuses) the relevant signal source for a held coin's original catalyst and exits early if the signal source explicitly reverses (e.g. a follow-up "sell" or confidence collapse on the same coin) rather than only reacting to price thresholds. Document the new exit path in `STRATEGY.md` and remove it from the structural-weaknesses list once shipped.
**Done when:** A unit test simulating a reversed signal on a held coin triggers an exit distinct from the existing stop-loss/take-profit/trailing-stop/max-age paths, and the full suite still passes.

**Result (2026-09-21):** Added `check_signal_reversal_exits` (`trader.py`) — runs once per cycle right after this cycle's pump+news signals are merged and deduplicated, before the generic signal-processing loop. It builds the set of coins with a fresh `action: "sell"` in that batch and, for any of those coins the bot currently holds *with a tracked entry price*, exits immediately regardless of P&L, logging `sell_signalreversal` (distinct from `sell_stoploss`/`sell_takeprofit`/`sell_trailingstop`/`sell_stale`, and from the generic loop's own `sell_signal`). It runs unconditionally on price — its trigger is the reversed thesis, not a threshold.

Two real things surfaced while wiring this in, both fixed same-day rather than left as gaps:

1. **Double-sell risk.** My first pass just called the new check and re-fetched `holdings` afterward, trusting the refreshed dict to keep the generic loop from reprocessing the same sell signal. Two existing live-mode tests in `tests/test_trader_coverage_gaps.py` caught the flaw immediately: their `get_holdings` mock is static (doesn't reflect an order just placed), so the same sell signal fired *twice* — once via the new reversal path, once via the old generic-loop path — double-counting `_wins`/`_losses`. Real Kraken holdings likely update fast enough in practice, but "likely fast enough" isn't a guarantee I wanted resting on for a live-money sell, so I made `check_signal_reversal_exits` return the set of coins it claimed and filtered those out of the `signals` list itself before the generic loop runs — correct regardless of how quickly the exchange reflects the trade.
2. **Scope of "claimed."** Initially the reversal check claimed a coin the moment it matched a sell signal, before checking whether a tracked position existed. That's wrong for a coin Kraken shows as held but `positions.json` has no record of (a manual trade, or the exact drift class Day 74's reconciliation script exists to catch) — the reversal check can't judge a thesis it never recorded, but silently dropping the sell signal (as claiming-before-checking did) would lose it entirely instead of letting the generic loop still execute it without pnl tracking, which is what the pre-Day-93 code did. Fixed by only marking a coin "claimed" after confirming both a tracked position and a live price are available; `tests/test_max_positions.py::test_sell_not_blocked_at_limit` (untracked-position case, no `get_position` mock) passes unchanged as a result, alongside two new dedicated cases in `tests/test_signal_reversal_exit.py`.

That reordering also made a branch of the generic loop's own live sell handling — the `if position: pnl = current_value - position["amount_cad"]; remove_position(coin)` block — permanently unreachable: any coin with both a tracked position and a fetchable price is now claimed upstream before that branch runs, and if price fetch fails the signal is skipped even earlier. Left as dead code, it would have quietly dropped `trader.py` off its Day-81/92 100%-coverage floor with nothing pointing at why. Simplified the branch to the one case that can still reach it (Kraken-held, locally-untracked, so `pnl` is always `None`) and updated `tests/test_trader_coverage_gaps.py`'s two live-sell tests (which had position mocks and are now covering the new reversal path, not the generic loop) plus added `test_live_sell_signal_untracked_position_places_order_without_pnl` to keep the untracked-position branch covered under its own name. `STRATEGY.md`'s exit-logic table, flowchart, and "Known structural weaknesses" section (this was the one open item, now closed and replaced with an honest note about the new check's actual limit — it only catches a reversal when the same cycle's broad headline scan happens to re-surface the coin, not via a dedicated per-position re-query, which would multiply Claude calls by open-position count every cycle) are updated to match.

Verified for real, Python 3.11 venv built fresh in this sandbox (system Python has no pytest/mypy, same as every prior day that needed them): `pytest -q --cov=. --cov-report=term-missing --cov-fail-under=95` → 478 passed (471 prior + 7 new: 6 in `tests/test_signal_reversal_exit.py`, 1 added to `tests/test_trader_coverage_gaps.py`), `trader.py` itself at 100% (was 96% after the initial two-test edits exposed the dead branch above), overall 98.18%, gate held. `python3 -m mypy --ignore-missing-imports trader.py` clean, and the existing `tests/test_trader_types.py` lock test (mypy + full-annotation AST audit) passes unchanged — `check_signal_reversal_exits` is fully type-hinted so it's covered by that lock without any edit to the lock test itself. `pip check` clean. The 7 pre-existing `tests/test_cli_flags.py` failures in this sandbox (missing `KRAKEN_API_KEY`/`KRAKEN_PRIVATE_KEY`/`ANTHROPIC_API_KEY` — no `.env` here, `.env` is intentionally never created per this project's safety rules) are unrelated to this change — confirmed via `git stash` against the pre-Day-93 tree (same 7 failures) and confirmed passing once those three vars are set to dummy values in the shell for a one-off check.

Not done, and can't be from this sandbox: the reversal check has not been exercised against a real Claude response reversing a real open position end-to-end (the mocked-signal unit tests prove the mechanism; Day 90's precedent of calling `market_matcher.analyze_news_for_trades()` directly against the live API doesn't apply here since there's no genuinely-held position with a stale thesis to test against in a $0.01-CAD dry-run account).

## Day 94: raise the CI coverage gate off its Day 83 floor
**Why:** `.github/workflows/test.yml`'s `--cov-fail-under=95` has been unmoved since Day 83, but real coverage has held at a stable 98%+ for the ten days since (confirmed again during the Day 91 sweep: 98.14%, 469 tests). Day 83's own comment in the workflow file says to raise the threshold "when coverage genuinely improves and stays there for a few days" — that condition has been true for a while now and nothing acted on it.
**Do:** Raise `--cov-fail-under` to a value close to (but with a couple points of headroom below) the current real percentage. Verify the new threshold still passes on the current suite and would fail on a synthetic drop (temporarily skip a test file, confirm CI-equivalent local run fails, then restore).
**Done when:** The workflow's coverage gate is raised, a local run against the current suite passes it, and a synthetic coverage drop below the new threshold fails as expected.

**Result (2026-09-22):** Found and fixed a small file-integrity bug while locating this task: the "## Day 94:" heading itself was missing from this file — Day 93's Result text ran directly into Day 94's `**Why:**` line with no header in between, so `grep '^## Day'` silently skipped it. Restored the heading above rather than leaving the gap for whoever reads this file next.

Built a fresh Python 3.11 venv in this sandbox (system Python has no pytest/coverage, same as every prior day needing them) and ran the CI-equivalent command directly: `pytest -q --cov=. --cov-report=term-missing --cov-fail-under=95` → 478 passed, 98.18% overall (`trader.py`, `kraken_client.py`, `config.py`, and 15 other modules at 100%; lowest is `scripts/daily_pnl.py` at 91%), matching Day 93's own verification exactly. Raised the gate from 95 to 96 — two points of headroom below the real 98.18%, mirroring Day 83's original ratio (95 set against a 98% baseline, roughly 3 points) rather than picking a number by feel. Verified the new threshold two ways: (1) reran the full suite with `--cov-fail-under=96` — passes, same 478 tests, same 98.18%; (2) synthetic drop — moved `tests/test_trader_coverage_gaps.py` out of `tests/` (the file covering most of `trader.py`'s 315 statements) and reran: 463 passed, `trader.py` fell to 86%, overall to 95.10%, and the gate correctly failed with `Required test coverage of 96% not reached`. Restored the test file immediately after (`git status` clean, confirmed no stray changes) rather than leaving the repo in the broken state.

Updated three places to keep the threshold consistent rather than just the workflow file: `.github/workflows/test.yml` (95 → 96, comment rewritten to explain the Day 94 bump and cite the actual baseline instead of just restating Day 83's old rationale), `Makefile`'s `coverage` target comment (pointed at the workflow file instead of hardcoding the number a second place it could drift), and `ISA.md`'s ISC-43 (both the checklist line and its Test Strategy table row, 95% → 96%) — the same kind of documentation-lags-code gap this project has hit repeatedly (README, STRATEGY.md, SECURITY.md, and now its own coverage number) is exactly what a five-minute grep-and-fix avoids. `STRATEGY.md` and `SECURITY.md` were checked and don't reference the coverage percentage, so no change needed there. Did not touch `--cov-fail-under=95` inside this Result note's own quoted Day-93 text (line 436) or Day 91/92's historical `95%`/`98.14%` mentions elsewhere in this file — those are dated records of what was true at the time, not live configuration, and rewriting history to match today's number would be the opposite of what this file is for.

Not verified from this sandbox (same standing blocker as Day 56/57/86/87/90): whether the new `--cov-fail-under=96` gate actually goes green on GitHub Actions' own runner once pushed — the local Python 3.11 venv run above is the CI-equivalent proxy this project has used every time real CI access wasn't available, not a substitute for watching the actual workflow run.

---

## Status note (added Day 95, 2026-09-23)

Day 94's own "Next:" line said there was nothing queued past it and to do a fresh survey pass, same as Days 66/79/91 — so that's today's starting point instead of assuming an unclaimed entry was sitting here. Built the Python 3.11 venv this project always needs for real verification (system Python still has neither pytest nor mypy) and re-ran the full CI-equivalent command first, to confirm Day 94's numbers before looking for new work rather than trusting the written record on faith: 471 passed + the same 7 known-and-explained `test_cli_flags.py` failures (missing `.env`, never created per this project's own safety rules — reconfirmed pre-existing by `git stash`), 97.76% coverage, the Day 94 gate (`--cov-fail-under=96`) held.

Then ran a mypy sweep, same method Day 91 used ("all `.py` files in the repo") — except this time actually including `scripts/`, which every prior mypy round (Days 15, 16, 68, 90, 91, 92) had silently skipped in favor of just the repo-root modules. First real finding: `scripts/archive_trades.py` had two `var-annotated` errors mypy had simply never had a chance to catch, since nothing had ever pointed mypy at the file — `archive_csv`/`archive_jsonl` both build their kept/archived lists via bare `x, y = [], []` unpacking with no way for mypy to infer an element type. This is a different class of gap than the five "clean but unlocked" rounds before it (market_matcher.py, then the 16-module batch): a live, unfixed type error sitting in a script that had genuinely never been checked, not a passing check with nothing pinning it in place. The other three scripts (`check_heartbeat.py`, `daily_pnl.py`, `reconcile_positions.py`) were already clean. Picked this as today's task rather than inventing a new backlog entry from scratch, since it's the same "the tracking files claim more coverage than actually exists" pattern this project keeps re-discovering, just found live during the survey instead of pre-written as a Do line.

## Day 95: mypy-clean and lock `scripts/`
**Why:** Every prior type-hint sweep (Days 15, 16, 68, 90, 91, 92) targeted only the repo-root `.py` modules. `scripts/` — `archive_trades.py`, `check_heartbeat.py`, `daily_pnl.py`, `reconcile_positions.py` — had never once been run through mypy, and doing so today found a real, currently-unfixed error, not just an unlocked-but-already-clean file.
**Do:** Run `mypy --ignore-missing-imports` across all four `scripts/*.py` files, fix whatever it surfaces, run the same AST full-annotation audit this project's other lock tests use, then write `tests/test_scripts_types.py` covering all four in one mypy invocation plus the AST check, mirroring `tests/test_remaining_modules_types.py`'s shape.
**Done when:** `python3 -m mypy --ignore-missing-imports scripts/*.py` returns zero errors, the AST audit passes for all four files, and the full suite (with coverage gate) still passes.

**Result (2026-09-23):** `archive_trades.py`'s two `var-annotated` errors were exactly what the survey found: `archive_csv` (line 64) and `archive_jsonl` (line 96) each built two lists via bare `x, y = [], []`, which mypy can't infer an element type for without an incompatible-usage error to hint from. Fixed with explicit annotations (`kept: list[list[str]] = []` / `archived: list[list[str]] = []` for the CSV rows, `list[str]` for the JSONL lines) rather than reaching for `# type: ignore`, matching this project's own stated preference (Day 92's `portfolio.py::compute_value` fix took the same approach over papering with an ignore comment). The AST full-annotation audit (the half of this exercise that actually found gaps on Days 68 and 92) came back clean on all four scripts this time — no bare or defaulted untyped parameters, no missing return annotations. Wrote `tests/test_scripts_types.py` mirroring `tests/test_remaining_modules_types.py`'s exact shape (one mypy subprocess call across the four targets, plus the AST walk).

Verified with the CI-equivalent command in a fresh Python 3.11 venv (system Python still has neither pytest nor mypy, same as every day before this one that needed them): `pytest -q --cov=. --cov-report=term-missing --cov-fail-under=96` → 473 passed (471 + this file's 2 new tests), same 7 pre-existing `test_cli_flags.py` failures (missing `.env` vars, confirmed unrelated via `git stash` — identical failures on the pre-change tree), 97.76% overall coverage, gate held. `python3 -m mypy --ignore-missing-imports *.py scripts/*.py` — all 27 source files, repo root and scripts together in one invocation for the first time — comes back clean. `pip check` clean. `scripts/archive_trades.py`'s own coverage moved from whatever it was before to 94% (six missed lines, all pre-existing edge-case branches unrelated to today's change) purely as a side effect of the two new statement-adjacent lines being exercised by the existing `tests/test_archive_trades.py` suite, which needed no changes.

Not verified from this sandbox (same standing category as Day 56/57/86/87/90/94): whether this passes on GitHub Actions' own runner once pushed, rather than just the local venv proxy this project has relied on throughout.

While in there, checked `README.md`/`STRATEGY.md`/`SECURITY.md` for the same kind of drift Days 64/66/75/82 have repeatedly found. `STRATEGY.md` is current — Day 93 already updated its exit-logic table, flowchart, and structural-weaknesses section for `check_signal_reversal_exits`, and `SECURITY.md` doesn't reference anything Day 93-95 touched. `README.md` is not current: its "Risk management" feature list (last regenerated Day 82) documents trailing-stop/stop-loss/take-profit/max-age exits but has no line at all for the Day 93 signal-reversal exit — a real, user-visible feature gap, not a cosmetic one, since it's the one exit path that isn't driven by price. Left unfixed today rather than scope-creeping this mypy-lock day into a second unrelated change; queued as Day 96 below.

## Day 96: README Features re-audit for the Day 93 signal-reversal exit
**Why:** Day 95's survey found `README.md`'s "Risk management" feature list (last regenerated Day 82) has no entry for `check_signal_reversal_exits` (Day 93) — the bot's one exit path that isn't driven by a price threshold, missing from the one doc most likely to be a stranger's first read of what this bot actually does.
**Do:** Add a bullet for the Day 93 signal-reversal exit to README's "Risk management" list (matching the existing bullets' one-line style) and to the "How It Works" numbered flow if it belongs there. While in there, do the same kind of full audit Day 82 did — check the rest of the Features list and the Mermaid diagram against the current module set, not just the one known gap.
**Done when:** README's Risk management list includes the Day 93 exit path, and a fresh pass finds no other gap against the current shipped-features list (or any found gap is fixed too, not just the one known one).

**Result (2026-09-24):** Added the Day 93 signal-reversal exit to README's Risk management list (`**Signal-driven reversal exit**`, worded to match the existing bullets' one-line style and explicitly called out as the one exit path that isn't price-driven) and to the "How It Works" numbered flow as its own step 6, ahead of the generic signal-merge/order-placement step it now runs before — matching `trader.py`'s real per-cycle order (reversal exits happen before the generic signal loop, per Day 93's own double-sell fix).

Did the rest of Day 82's full-audit pass rather than stopping at the one known gap, and found real drift beyond it — built a Python 3.11 venv (system Python here is already 3.11.15, so no separate build needed this time) and ran the CI-equivalent command to get real current numbers instead of trusting the written record: `pytest -q --cov=. --cov-report=term-missing --cov-fail-under=96` → 473 passed, same 7 pre-existing `test_cli_flags.py` failures Day 93/94/95 already documented (missing `.env`, confirmed unrelated), 97.76% coverage, gate held — matching Day 95's numbers exactly. `pytest --collect-only -q` shows **480 tests collected across 57 test files** (`ls tests/*.py | wc -l`), not the README's stale "52 test files / 466 tests" (last updated Day 64/82's era). Fixed both counts in the Project Structure tree and the Tech Stack line.

Two more real gaps, not cosmetic: (1) `.env.example` actually documents **27** variables (`grep -oE '^[A-Z_][A-Z0-9_]*=' .env.example | wc -l`), not the 26 the Setup section claims — the file itself is correctly kept in sync with `config.py` by `tests/test_env_example.py` (reran it standalone, 3 passed), but the prose number describing *how many* was never bumped when the 27th var was added. (2) The Tech Stack line's mypy claim — "locked on `kraken_client.py`, `trader.py`, `config.py`, `notifier.py`, `status.py`, and `blacklist.py`" — has been stale since Day 92 at the latest: `ls tests/*types*.py` shows six lock-test files now (`test_kraken_client_types.py`, `test_trader_types.py`, `test_config_notifier_status_blacklist_types.py`, `test_market_matcher_types.py`, `test_remaining_modules_types.py`, `test_scripts_types.py`) covering all 27 source files (`ls *.py scripts/*.py | wc -l`) — repo root and `scripts/` together — not the original six-file list from Days 15/16/68. Reworded to describe the mechanism (mypy-clean + AST full-annotation audit, enforced via the `test_*_types.py` suite) instead of naming files, so it can't drift the same way again as new modules get locked. Also updated the coverage bullet ("98%+ as of Day 81" → the real 97%+ against the Day-94-raised 96% gate) since it was sitting on a stale Day-81 anchor point three coverage-gate changes later.

Checked the Mermaid diagram and Project Structure tree against the current module set: both are accurate (root `.py` files diffed 1:1 against the tree's `.py` entries, zero mismatch; `claude-opus-4-6` in the diagram matches `market_matcher.py`'s actual model string). No new node needed for the reversal exit — it's internal to `trader.py`'s existing box, same as the other three price-based exit paths, none of which get their own diagram node either. `STRATEGY.md` and `SECURITY.md` were already confirmed current by Day 95's pass; not re-checked today since nothing shipped since that would touch them.

Not verified from this sandbox (same standing category as Day 56/57/86/87/90/94/95): whether the Mermaid block renders without syntax errors on GitHub's actual renderer, since this environment has no way to preview it — same gap Day 64 and Day 82 both already noted honestly rather than claiming a visual check that didn't happen.

---

## Status note (added Day 97, 2026-09-25)

Day 96's own "Next:" line said nothing was queued and to do a fresh survey pass, same as Days 66/79/91/94→95. Re-ran the CI-equivalent command first (473 passed, same 7 known `.env`-related `test_cli_flags.py` failures, 97.76% coverage, 96% gate held — matching Day 96 exactly) and a full mypy sweep across all 27 source files (root + `scripts/`) — clean, nothing new since Day 95 locked the last of it. Found the real gap on the GitHub side instead of the code side: 5 Dependabot PRs (#6-#10 — anthropic, krakenex, types-requests, python-dotenv, pytest-cov) had been open since 2026-09-14, about 11 days, well past the weekly cadence Day 88 documented in `OPS_RUNBOOK.md` section 10. Same root pattern as Day 86 the first time this happened: Dependabot isn't the thing that fails, nobody was checking. Picked this as today's task rather than inventing a new backlog entry, same reasoning Day 95 used for the `scripts/` mypy gap.

## Day 97: review the 5 open Dependabot PRs (11 days stale, past the Day 88 cadence)
**Why:** `OPS_RUNBOOK.md` section 10 (Day 88) names a weekly review cadence for open Dependabot PRs specifically because Day 86's 2+ week backlog happened once already. It happened again — 5 PRs open since 2026-09-14, none crossing a major-version ceiling already pinned in `requirements.txt` (all just raise the floor within the existing `<X.0.0` bound), but unreviewed all the same.
**Do:** Review and merge each of the 5 open PRs individually, verifying locally per `SECURITY.md`'s bump procedure (`pip install -r requirements.txt && pytest -v && pip-audit -r requirements.txt`), not as a batch — same discipline as Day 86.
**Done when:** All 5 PRs are either merged (verified) or explicitly closed with a documented reason, matching Day 86's done-when bar.

**Result (2026-09-25):** Reviewed all 5: `pytest-cov` (#10, →7.1.0), `python-dotenv` (#9, →1.2.3), `types-requests` (#8, →2.33.0.20260906), and `krakenex` (#7, →2.2.2) merged cleanly through GitHub (`mcp__github__merge_pull_request`, squash), each a same-major-ceiling floor bump with CI already green on the PR's own head commit before merging. `anthropic` (#6, →1.6.0) reported `mergeable_state: dirty` — its branch was based on Day 92's `main` (11 days stale) despite the diff being one non-overlapping `requirements.txt` line, same situation Days 86/89/90 hit with PRs #1 and #3. Applied the identical one-line bump directly to `main` (commit `731c0a2`) instead of forcing the merge, and closed PR #6 with a comment pointing to the commit, matching Day 89's precedent exactly.

Verified for real before and after each merge, not just trusted GitHub's green check: built on the existing Python 3.11 venv (system Python here is 3.11.15, no separate build needed, same as Day 96), ran `pip install -r requirements.txt` (already resolved `anthropic` to 1.8.0, `krakenex` to 2.2.2, `pytest-cov` to 7.1.0, `python-dotenv` to 1.2.3, `types-requests` to 2.33.0.20260906 — all at or above every PR's proposed floor, before any `requirements.txt` edit — because the existing lower bounds already permitted them), then `pytest -q --cov=. --cov-report=term-missing --cov-fail-under=96` → 473 passed, same 7 pre-existing `test_cli_flags.py` failures (missing `.env`, confirmed unrelated every prior day this came up), 97.76% coverage, gate held — matching Day 96's numbers exactly, both before touching anything and again after the `anthropic` edit landed. `python3 -m mypy --ignore-missing-imports *.py scripts/*.py` clean across all 27 files both times. `pip-audit -r requirements.txt`: no known vulnerabilities, before and after.

None of the 5 crossed a major-version ceiling already pinned in `requirements.txt` (every `<X.0.0` upper bound stayed the same), so the stricter Day-86 bar — read the real migration guide, don't trust a mocked-out test suite alone — doesn't strictly apply the way it did for pytest 9.x (Day 89) or anthropic 1.x itself (Day 90). Read `anthropic`'s 1.6.0 release notes anyway since it's the one call site (`market_matcher.py`) with any safety weight: new Managed Agents/compaction/geo-field features and retry-header fixes, nothing touching the `Message`/content-block surface `market_matcher.py` and its Day-90/91 `isinstance(block, anthropic.types.TextBlock)` guard depend on — and the venv already had 1.8.0 resolved and passing before the edit, a version ahead of the PR's own 1.6.0 target, so the verification run was never against a version older than what's now pinned.

Confirmed via GitHub after all 5: 0 open pull requests, and all 5 landed commits (the 4 merges plus the direct `anthropic` commit) show green on GitHub's own "Tests" Actions runner, not just the local venv proxy — closing the same standing verification gap (Days 56/57/86/87/90/94/95/96 all noted "not verified on GitHub's actual runner" for one thing or another) for this specific piece of work, since GitHub Actions status was directly checkable this time via the GitHub MCP tools, unlike a Mermaid-render or VPS-SSH check.
