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
