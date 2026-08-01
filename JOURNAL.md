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

---

## Day 6, 2026-05-26

**Shipped:** Authored `.env.example` covering every env var in `config.py`. Grouped into five sections — Secrets (Kraken API key, Kraken private key, Anthropic API key), Risk caps (MAX_TRADE_AMOUNT, MIN_CONFIDENCE, DAILY_LOSS_LIMIT), Exit thresholds (STOP_LOSS_PCT, TAKE_PROFIT_PCT), Cadence (RUN_INTERVAL_MINUTES), and Master switch (DRY_RUN). Each variable has a one or two line comment explaining what it does and how it interacts with the strategy. Header at the top documents the cp + edit workflow. `DRY_RUN=true` is the example default so anyone cloning the repo cannot accidentally go live.

**Surprised by:** How many of these variables I've already documented elsewhere (STRATEGY.md, OPS_RUNBOOK.md, the project ISA). `.env.example` is the only one of those four that lives *inside* the development workflow — every other doc reaches into it. That's the right shape for a config template.

**Next:** Day 7, add a Mermaid architecture diagram to `README.md` under a new "Architecture" section.

---

## Day 7, 2026-05-27

**Shipped:** Added an `## Architecture` section to `README.md` between `## How It Works` and `## Setup` so a top-down skim hits the diagram early. The Mermaid block is a left-to-right flowchart with three subgraphs (External sources, Signal layer, and the unwrapped trader-and-client core) and twelve edges. External sources include the RSS feeds + Nitter accounts, the Kraken blog RSS, the Kraken Ticker API, and Anthropic Claude. The signal layer holds news_fetcher, market_matcher, listing_monitor, and pump_detector. The trader merges all three signal streams, persists positions to disk, and routes orders through kraken_client to the Kraken Exchange REST API. A short intro paragraph above the diagram links to STRATEGY.md for the full math.

**Surprised by:** GitHub's Mermaid renderer handles `<br/>` line breaks and emoji-free subgraph labels well, but it does NOT like unquoted node labels with dots or parentheses. Wrapped every label in double quotes (`["text"]`) up front to avoid the render-then-debug cycle.

**Next:** Day 8, write `SECURITY.md` covering API key storage, key rotation, kill switch, network exposure, dependency policy, and incident response.

---

## Day 8, 2026-05-28

**Shipped:** Authored `SECURITY.md` as the working threat model. Six required topics, each with a Threat, Posture, and Concrete actions block. API key storage section names the Kraken permission set the bot needs (Query Funds, Query Open Orders, Modify Orders, Create/Cancel Orders — withdrawal off) and gives a one-liner to grep the git history for accidental commits. Key rotation lays out the two-key-window procedure with `sed` recipes against `.env`. Kill switch documents the two existing halt mechanisms (`DRY_RUN=true` and `systemctl stop`) and points at Day 24's planned file-based kill switch. Network exposure section gives the `nmap` audit command, the sshd_config grep recipe, and an SSH login-attempts review. Dependency policy names `pip-audit` and a one-dep-at-a-time upgrade workflow. Incident response is a four-phase runbook (STOP → CAPTURE → INVESTIGATE → RECOVER) with copy-pasteable commands at every step. Closes with a hardening backlog mapping each future security item to its target backlog day.

**Surprised by:** Writing the incident response section made me realize that without a JSONL trade log (Day 20) the forensic capture relies on `trades.csv` which is append-only but easy to corrupt. The Day 20 work just became more important than I had it scored.

**Next:** Day 9, add the pytest scaffold (conftest.py with a `kraken_dryrun` fixture, tests folder, pytest in requirements.txt).

---

## Day 9, 2026-05-29

**Shipped:** Pytest scaffold. Added `pytest>=8.0.0` and `pytest-mock>=3.12.0` to `requirements.txt`. Created `tests/__init__.py`, `tests/conftest.py` with the `kraken_dryrun` fixture, and `tests/test_smoke.py` to prove the rig works. The fixture returns a `MagicMock` shaped like a `krakenex.API` client with `query_private` and `query_public` preloaded with canned responses for `Balance`, `OpenOrders`, `AddOrder`, `CancelOrder`, `AssetPairs`, and `Ticker` — every endpoint `kraken_client.py` actually calls. Tests can override per-endpoint with `side_effect` or replace return values directly. Updated `.gitignore` to exclude `venv/`, `.venv/`, and `.pytest_cache/` so the local venv never gets committed.

Verified end to end: `./venv/bin/pytest --collect-only` exits 0 with 3 tests discovered; `./venv/bin/pytest -v` runs all 3 and they pass.

**Surprised by:** `pytest --collect-only` with an empty `tests/` folder exits 5 ("no tests collected"), not 0. The done-when says exit 0. Caught it before shipping by adding a smoke test that exercises the fixture itself — also serves as a worked example for Days 10-12 when real per-module tests land.

**Next:** Day 10, write `tests/test_market_matcher.py` — at least two tests covering a known coin match and an unknown coin handled gracefully.

---

## Day 10, 2026-05-30

**Shipped:** First real unit tests against `market_matcher.analyze_news_for_trades`. Six test functions, eight test cases (one parametrized over DOGE/SHIB/PEPE). All mock `client.messages.create` via `mocker.patch.object` so no network calls fire. Covered branches:
1. Happy path — a 0.95-confidence buy on a known coin survives MIN_CONFIDENCE (parametrized x3)
2. Low confidence filter — a 0.30-confidence signal is dropped
3. Unknown coin — Claude hallucinating a non-existent ticker does NOT crash (passes through; trader layer's `get_price` returns 0 and skips)
4. Malformed JSON — non-JSON output is caught by the JSONDecodeError handler, returns `[]`
5. Fenced code block — the ` ```json ... ``` ` wrapping is stripped before parse
6. Anthropic exception — any RuntimeError from the SDK is caught, returns `[]`

Full suite: 11 passed (3 smoke + 8 matcher).

**Surprised by:** The function doesn't enforce that Claude's returned coins are in the `available_coins` list — it trusts whatever comes back. The trader layer's `get_price` is the actual safety net. That asymmetry is now pinned by a test, so any future tightening will have a place to land.

**Next:** Day 11, write `tests/test_news_fetcher.py` — mock `feedparser.parse` and verify happy path, no-title skip, and link-based dedupe.

---

## Day 11, 2026-05-31

**Shipped:** Six tests for `news_fetcher.fetch_top_headlines` and the `format_headlines_for_prompt` helper. All mock `feedparser.parse` and stub `fetch_twitter_signals` to `[]` so RSS-only behavior is isolated and no network calls fire. Cases:

1. Happy path — three RSS entries become three correctly-shaped dicts with `title`, `summary`, `source: "news"`
2. No-title skip — entries with empty or missing `title` are filtered out
3. Title dedupe across feeds — the same headline syndicated to all six RSS feeds appears once (the code dedupes by **title**, not by link as the backlog assumed)
4. `max_articles` cap — `fetch_top_headlines(max_articles=5)` truncates to 5
5. Formatter emoji prefixes — `📰` for RSS, `🐦` for Twitter
6. Feedparser exception resilience — one feed raising does not crash the function

Full suite: 17 passed (3 smoke + 8 matcher + 6 news_fetcher).

**Surprised by:** The backlog said "deduplicates by link" but the code dedupes by title. Reasonable design — RSS items often have the same article re-syndicated under different links — but worth knowing for future. I pinned the actual behavior with a test; if the dedup key ever changes to link, that test will fail and signal the contract shift.

**Next:** Day 12, write `tests/test_kraken_client.py` — happy path on a known Balance response shape and a 5xx-raises-sensible-exception path.

---

## Day 12, 2026-06-01

**Shipped:** 11 tests for `kraken_client` covering the wrapper boundary — every function the trader calls. All reuse the `kraken_dryrun` fixture from `conftest.py` so no `requests-mock` dependency added. Cases:

- `get_balance`: happy path (100.00 CAD from default fixture), CAD→USD fallback, Kraken error → 0.0, empty wallets → 0.0
- `get_holdings`: extracts non-fiat non-zero balances with cleaned tickers; Kraken error → `{}`
- `get_tradable_coins`: returns sorted CAD/USD coin list with fiat removed
- `get_pair`: returns `None` for unknown coins
- `get_price`: returns `0.0` for unknown coins
- `place_order`: rejects zero-volume trades; returns `None` when no pair found

Full suite: 28 passed (3 smoke + 8 matcher + 6 news_fetcher + 11 kraken_client).

**Surprised by:** Two backlog mismatches with reality. Backlog said `requests-mock` and `KrakenClient.get_balance()` raises on HTTP 5xx — but `kraken_client.py` is shaped as free functions over a `krakenex.API` instance, and on Kraken-returned errors it logs and returns `0.0` (or `None`/`{}` depending on function). Tests pin the actual contract. Switching error paths to *raise* would let the trader differentiate "Kraken is down" from "Kraken says balance is zero" — that's a future hardening candidate, not Day 12 scope.

**Next:** Day 13, add GitHub Actions CI workflow (`.github/workflows/test.yml`) that runs `pytest` on Python 3.11; add a status badge to the top of README.

---

## Day 13, 2026-06-02

**Shipped:** GitHub Actions CI. New `.github/workflows/test.yml` triggers on push to main and on pull requests, runs on `ubuntu-latest` with Python 3.11, caches pip, installs full `requirements.txt`, and runs `pytest -v`. Placeholder env vars for `ANTHROPIC_API_KEY`, `KRAKEN_API_KEY`, and `KRAKEN_PRIVATE_KEY` are baked into the job so the Anthropic SDK constructor in `market_matcher.py` (runs at module-load) doesn't blow up — tests mock all real network calls, the placeholders only satisfy the SDK's "must be set" guard. Added the Tests status badge to the top of `README.md` right below the title so it shows on the repo home page.

**Surprised by:** First CI run on the Day 13 commit (`1dcf3aa`) went RED. Two `test_kraken_client.py` tests assumed Evan's local WIP `clean_asset()` refactor of `kraken_client.py`, but CI checks out HEAD which uses the simpler `key.lstrip('X').lstrip('Z')` variant. Locally the tests ran against the working tree (with WIP) so they were green; on CI they hit the HEAD code path and failed. Fast-follow commit `ccdeae4` made the tests accept either ticker form ("DOGE"/"XDG"/"DG" and "BTC"/"XBT"/"BT") so they pass against both versions. Second CI run: 28/28 passed, 24 seconds end-to-end. Badge resolves green.

The deeper lesson: tests that assume working-tree state, not committed-tree state, will lie to you about CI readiness. From here forward, simulate CI locally with `git stash push <wip>` before claiming a test file is portable.

**Next:** Day 14, replace every `print()` in the trading modules with a proper `logging` call; the root logger config moves into `main.py`.

---

## Day 14, 2026-06-03

**Shipped:** Logging configuration audit + format upgrade. Audited the trading modules with the exact done-when probe: `grep -rn "print(" *.py` returns zero matches — every module already uses `logger = logging.getLogger(__name__)` and proper level methods. The remaining gap was the format string in `main.py`: it read `"%(asctime)s [%(levelname)s] %(message)s"` (no module name); the Day 14 backlog spec is `"[%(asctime)s] %(levelname)s %(name)s: %(message)s"`. Updated `main.py` to use the spec format. Now every log line in journalctl reveals which module emitted it (kraken_client, market_matcher, pump_detector, etc.) — searchable observability gain.

Locked the contract with `tests/test_logging_config.py`: 13 tests covering the required format string, INFO level, both handlers (stream + file), no-bare-`print()` audit parametrized over all 9 trading modules, and a getLogger smoke check.

Full suite: 41 passed (3 smoke + 8 matcher + 6 news_fetcher + 11 kraken_client + 13 logging_config).

**Surprised by:** The hardest part of "replace print with logging" was that there were no print calls left to replace. The real work was the format string — adding `%(name)s` so logs become greppable by module. Writing the test first surfaced the misalignment in 5 seconds.

**Next:** Day 15, add type hints to every function in `kraken_client.py` and get `mypy --ignore-missing-imports kraken_client.py` to zero errors.

---

## Day 15, 2026-06-04

**Shipped:** Full type hints on every function in `kraken_client.py` — `get_client`, `get_balance`, `get_holdings`, `get_tradable_coins`, `get_pair`, `get_price`, `place_order`. Used `from __future__ import annotations` so modern syntax (`dict[str, float]`, `list[str]`) works on Python 3.8+. `get_pair` and `place_order` now correctly declare `Optional[str]` / `Optional[dict]` returns since both return None on failure paths. `client: krakenex.API` everywhere — mypy treats it as Any (krakenex has no stubs) but the readable annotation documents intent. Added `mypy>=1.0.0` to `requirements.txt` so CI runs the same toolchain.

Locked the contract with two tests in `tests/test_kraken_client_types.py`:
1. `mypy --ignore-missing-imports kraken_client.py` returns zero errors — the done-when probe verbatim, runs in CI now
2. AST audit — every function in `kraken_client.py` has annotations on every arg and a return annotation. Catches future regressions (someone adding an untyped helper).

Edits were signature-only (no body changes) so Evan's still-stashed `clean_asset` refactor pops back on top with no conflict.

Verified: `mypy --ignore-missing-imports kraken_client.py` → "Success: no issues found in 1 source file"; full suite 43 passed.

**Surprised by:** `get_pair` was declared `-> str` but returns `None` for unknown coins — silent lie in the old signature that the test suite never caught (the existing test only asserted `is None`, not the type). Day 15 made me read the existing signature carefully and the `Optional[str]` upgrade is a real correctness gain, not just decoration.

**Next:** Day 16, type hints on `trader.py` with the same `mypy --ignore-missing-imports trader.py` zero-error gate.

---

## Day 16, 2026-06-05

**Shipped:** Full type hints on `trader.py`. Both functions annotated — `check_exit_conditions(client: krakenex.API, holdings: dict[str, float]) -> None` and `run_trading_cycle() -> None` — plus the module-level `_starting_balance: Optional[float] = None`. Used `from __future__ import annotations` for forward syntax compat.

Added `mypy.ini` at the repo root with `follow_imports = silent` and `ignore_missing_imports = True`. This makes per-file mypy probes self-contained: mypy reads transitive imports for inference but only reports errors in the named file. The Day 15 + Day 16 + future "type module X" days each get a clean done-when gate without needing to fix every other module first.

**Real bug surfaced and fixed:** When I typed `trader.py`, mypy correctly flagged that `trader.py:195` calls `positions.log_trade(..., pnl)` where `pnl` is `Optional[float]`, but `positions.log_trade` was declared `pnl: float = None` — an implicit-Optional signature bug. One-line surgical fix to `positions.py`: changed the signature to `pnl: Optional[float] = None` (and added `from __future__ import annotations` + `from typing import Optional`). Both `positions.py` and `trader.py` are now signature-correct on the pnl pathway.

Contract locked with `tests/test_trader_types.py` (mirrors `test_kraken_client_types.py`): mypy probe + AST audit of every function signature.

Verified: `mypy --ignore-missing-imports trader.py` → "Success: no issues found in 1 source file"; Day 15 probe still clean; full suite 45 passed.

**Surprised by:** The mypy noise from transitive imports (14 errors before any work) was *almost all* historical drift — implicit Optional, missing requests stubs, Anthropic SDK union types — that had nothing to do with trader.py. Per-file mypy config is the right discipline for an existing untyped codebase: don't try to fix everything at once, fix one module per day.

**Next:** Day 17, extract a `Config` dataclass from `config.py` so callers get attribute access (`c.max_trade_amount`) instead of module globals, and update every callsite.

---

## Day 17, 2026-06-08

**Shipped:** `config.py` is now a frozen `Config` dataclass with a `Config.from_env()` classmethod and a module-level `cfg = Config.from_env()` singleton for ergonomics. Every env var is one typed field — `kraken_api_key`, `kraken_private_key`, `anthropic_api_key`, `max_trade_amount`, `min_confidence`, `daily_loss_limit`, `stop_loss_pct`, `take_profit_pct`, `run_interval_minutes`, `dry_run`. Secrets are `Optional[str]` (None is permissible at construction time; the bot's first private REST call is when a real key matters). Numerics get the right scalar types.

Updated all four callers:
- `main.py`: `RUN_INTERVAL_MINUTES` → `cfg.run_interval_minutes`
- `trader.py`: `MAX_TRADE_AMOUNT`, `DAILY_LOSS_LIMIT`, `DRY_RUN`, `STOP_LOSS_PCT`, `TAKE_PROFIT_PCT` → `cfg.*` (kept the documentation string `"Set DRY_RUN=false in .env to go live"` untouched since that names the env var, not a Python reference)
- `kraken_client.py`: `KRAKEN_API_KEY`, `KRAKEN_PRIVATE_KEY` → `cfg.*`
- `market_matcher.py`: `ANTHROPIC_API_KEY`, `MIN_CONFIDENCE` → `cfg.*`
- `tests/test_market_matcher.py`: `mm.MIN_CONFIDENCE` → `mm.cfg.min_confidence`

Contract locked with `tests/test_config.py` (6 tests): Config is a frozen dataclass, `Config.from_env()` returns an instance, the `cfg` singleton is a Config, every expected field is present (set-equality against an authoritative list catches both missing and rogue additions), field types match intent, frozen blocks mutation.

Verified: done-when probe `from config import Config; c = Config.from_env()` runs and returns a populated Config. mypy clean on trader, kraken_client, and config. Full suite 51 passed (45 prior + 6 new).

**Surprised by:** The `test_no_bare_print_calls_in_trading_modules[config.py]` test failed first because the original docstring example had `print(cfg.max_trade_amount)` as a usage demo — the AST-free regex audit (intentionally simple) doesn't distinguish docstrings from code. Changed the example to `use(cfg.max_trade_amount)` rather than make the audit smarter. The simpler rule reads cleaner and catches real bugs faster than a complex one that has to understand Python lexical scopes.

**Next:** Day 18, add `tenacity` retries with exponential backoff to every Kraken API method in `kraken_client.py`.

---

## Day 18, 2026-06-09

**Shipped:** `tenacity` retries on every Kraken API call. Added `tenacity>=8.0.0` to requirements. Rewrote `kraken_client.py` around two private helpers — `_call_private` and `_call_public` — that are the only functions that actually touch the network. Both are wrapped with a shared `_retry_kraken` decorator: `stop_after_attempt(3)`, `wait_exponential(min=1, max=10)`, `before_sleep_log` so every retry attempt logs at WARNING level. The six public functions (`get_balance`, `get_holdings`, `get_tradable_coins`, `get_pair`, `get_price`, `place_order`) delegate to the helpers and inherit retry for free.

Transient (retried) errors are classified by substring match in a small allowlist: `EAPI:Rate limit`, `EService:Unavailable`, `EService:Busy`, plus Python `ConnectionError` / `TimeoutError` if krakenex raises at the HTTP layer. Non-transient errors (`EAPI:Invalid key`, `EOrder:Invalid arguments`, etc.) return immediately — wasting retries on auth bugs and validation errors is worse than failing fast.

Contract locked with `tests/test_kraken_retry.py` (6 tests, all running in ~0.1s with `wait_none()` monkeypatch):
1. **AST audit** — every public Kraken function must call either `_call_private` or `_call_public`; calling `client.query_private(...)` directly is flagged. Catches future regressions.
2. **Rate-limit retry then succeeds** — `EAPI:Rate limit` × 2 + success → final value returned, `query_private` called exactly 3 times
3. **Rate-limit exhausts retries** — `EAPI:Rate limit` × 5 → `stop_after_attempt(3)` caps invocations at 3, function returns the default (0.0)
4. **Service-unavailable is also transient** — same retry contract on `EService:Unavailable`
5. **Invalid-key does NOT retry** — non-transient error returns immediately, exactly 1 invocation
6. **Public Ticker also retries** — verifies `_call_public` path through `get_price → get_pair → _call_public`

Also fixed the old `test_get_balance_returns_zero_on_kraken_error` etc. tests — they mocked `EService:Unavailable` which is now in the transient set; switched them to `EAPI:Invalid key` so they pin "non-retryable error → returns default" without triggering retries.

Full suite: 57 passed in 1.22s (51 prior + 6 new).

**Surprised by:** Tenacity's `wait_exponential(min=1, max=10)` works perfectly in prod but makes test runs painfully slow if you don't override it. The `wait_none()` monkeypatch via `mocker.patch.object(kc._call_private.retry, "wait", wait_none())` was the cleanest pattern — applied per-test via a fixture so production behavior stays the configured exponential.

**Next:** Day 19, rate limiter for Kraken calls — minimum 1 second between API calls, verified by a unit test.

---

## Day 19, 2026-06-10

**Shipped:** Manual `time.monotonic`-based rate limiter inside `kraken_client.py`. Added `MIN_CALL_INTERVAL_SEC = 1.0` module constant and a `_rate_limit()` function that uses `time.monotonic` (DST/NTP-safe) to enforce a minimum 1-second gap between calls. Wired into both `_call_private` and `_call_public` so every Kraken REST call passes through the limiter before hitting the network. The limiter sits *inside* the `@retry` helper so each retry attempt also honors the gap — no retry-storms during volatility.

Contract locked with `tests/test_kraken_rate_limit.py` (6 tests):
1. **Back-to-back calls sleep** — two calls 0.3s apart trigger `time.sleep` with delay ≈ 0.7s
2. **Constant matches spec** — `MIN_CALL_INTERVAL_SEC == 1.0`
3. **Elapsed interval skips sleep** — call 2.0s later does NOT sleep
4. **Cold start doesn't sleep** — first call ever doesn't pause
5. **`_call_private` invokes the limiter** — every private REST helper goes through `_rate_limit`
6. **`_call_public` invokes the limiter** — every public REST helper too

Added an autouse fixture `reset_kraken_rate_limiter` to `tests/conftest.py` that resets `_last_call_monotonic = 0.0` and patches `kraken_client.time.sleep` for every test. Without this, every test in `test_kraken_client.py` paid up to 1s of real sleep per call — the full suite went from 1.22s to 12.93s. With the autouse patch, back to 1.45s.

Full suite: 63 passed (57 prior + 6 new).

**Surprised by:** The rate-limit assertion `0.6 < delay <= 0.7` failed with `0.7000000000000028 <= 0.7` — float arithmetic precision. Loosened to `< 0.71` with a tiny epsilon. Standard pattern for testing floating-point bounds, easy to miss on first write.

**Next:** Day 20, JSONL trade events — replace `trades.csv` with `trades.jsonl`, append one structured event per trade, gitignore the file.

---

## Day 20, 2026-06-11

**Shipped:** Structured trade events as JSONL alongside the legacy CSV. `positions.log_trade` now appends one JSON object per trade to `trades.jsonl` with every field the backlog spec calls for — `timestamp`, `pair`, `side`, `volume`, `price`, `order_id`, `signal_source` — plus `coin`, `amount_cad`, `pnl_cad` for richer queries. The existing `trades.csv` keeps getting written so downstream tooling doesn't break (Day 23's `daily_pnl.py` will be the first new consumer of either format).

Two key design choices:
1. **Action decomposition.** Trader.py's existing calls pass `action` like `"buy_signal"`, `"sell_stoploss"`, `"buy_newlisting"`. `log_trade` splits this into `side` (`buy`/`sell`) and `signal_source` (`signal`/`stoploss`/`takeprofit`/`newlisting`). JSONL is now queryable on either axis without changing any caller.
2. **`pair` and `order_id` as keyword-only kwargs with `None` defaults.** Current trader.py callers don't have either at hand — both default to `null` in the JSONL. Future days can plumb the Kraken txid through `place_order`'s return value and pass it here.

`.gitignore` extended to exclude runtime state: `trades.jsonl`, `trades.csv`, `positions.json`, `seen_listings.json`, `last_run.txt`, `latest_status.json`. Six lines, one comment.

Contract locked with `tests/test_log_trade_jsonl.py` (13 tests, all in `tmp_path` so writes never pollute the repo):
1. Single call → one valid JSON line
2. All 7 required backlog fields present + 3 extras
3. Action decomposition parametrized over all 5 trader.py patterns (`buy_newlisting`, `buy_signal`, `sell_signal`, `sell_stoploss`, `sell_takeprofit`)
4. Multiple calls → multiple valid lines
5. Optional pair/order_id default to `null` (current trader.py path)
6. Optional pair/order_id round-trip when passed (future path)
7. CSV still written alongside (backward compat)
8. **Done-when probe verbatim** — `python3 -c "import json; [json.loads(l) for l in open('trades.jsonl')]"` exits 0
9. `.gitignore` excludes `trades.jsonl`

Full suite: 76 passed (63 prior + 13 new) in 2.54s.

**Surprised by:** The verbatim done-when probe uses `open('trades.jsonl')` which means the test had to be CWD-aware. `pytest`'s `tmp_path` + `monkeypatch.chdir(tmp_path)` is the clean pattern — every test writes to its own temp dir and the probe runs against that dir's file. Without that, parallel tests would collide on the repo's `trades.jsonl`.

**Next:** Day 21, heartbeat file `last_run.txt` — write ISO timestamp at the end of every cycle so `stat -f %m` answers "is the bot alive?" without SSH.

---

## Day 21, 2026-06-15

**Shipped:** Heartbeat file so "is the bot alive?" is answerable without SSH. New `heartbeat.py` exposes `write_heartbeat()` (writes the current UTC ISO 8601 timestamp to `last_run.txt`, returns it) and `read_heartbeat()` (parses it back to a tz-aware `datetime`, or `None` when missing/empty — for ops scripts and the future Day 31 deploy health check). Default path is resolved relative to the module, not CWD, so it writes the right file no matter where the bot is launched from.

**Key design choice — wrap, don't sprinkle.** `run_trading_cycle` has four exit paths (daily-loss-limit hit, insufficient balance, no signals, normal end). Rather than dropping a heartbeat write before every `return`, `main.py` now wraps the cycle in `run_cycle()` — call the trader, then stamp the heartbeat. One write site, and it survives any early-return path a future day adds to the trader. A raised exception intentionally skips the stamp: heartbeat means "a cycle completed," not "a cycle started."

`last_run.txt` was already in `.gitignore` (added preemptively on Day 20 alongside the other runtime-state files), so the gitignore half of the done-condition was already satisfied — verified with `git check-ignore`.

Contract locked with `tests/test_heartbeat.py` (4 tests, all in `tmp_path`):
1. Write produces a parseable ISO 8601 timestamp, tz-aware not naive
2. Write overwrites a stale previous stamp
3. `read_heartbeat` on a missing file → `None`
4. `read_heartbeat` on an empty/whitespace file → `None`

End-to-end probe: `write_heartbeat()` wrote `2026-06-15T23:04:49.772299+00:00` and `read_heartbeat()` round-tripped it. Full suite: 80 passed (76 prior + 4 new) in 1.88s.

**Surprised by:** The done-condition was already half-built. Day 20's gitignore sweep listed `last_run.txt` a day before the heartbeat existed — past-me front-ran the backlog. Worth noting the pattern: batching all runtime-state gitignore entries at once is cheap and removes a step from every later observability task.

**Next:** Day 22, API latency logging — wrap each Kraken API method to time the call and `logger.info("kraken.<method> took %.2fs")`, so slow responses surface before they become an outage.

---

## Day 22, 2026-06-16

**Shipped:** API latency logging on every Kraken call. Both network helpers — `_call_private` and `_call_public` — now bracket the actual `client.query_*` call with `time.monotonic()` and emit `kraken.<private|public>/<endpoint> took N.NNs` at INFO. Because the Day 18 retry refactor funnels *every* public function (get_balance, get_holdings, get_tradable_coins, get_pair, get_price, place_order) through these two helpers, every method gets per-call latency logging for free, tagged with the exact endpoint — better granularity than the backlog's "per method" framing, since `AssetPairs` and `Ticker` are now distinguishable in the logs.

**Key design choice — time the network, not the gate.** The timer starts *after* `_rate_limit()`, so our own 1s throttle never pollutes the measured latency. The number in journalctl is real Kraken round-trip time, which is the whole point: a creeping `kraken.public/Ticker took 2.40s` is the early warning for an upcoming outage, and it'd be useless if it secretly included our rate-limit sleep.

Contract locked with `tests/test_kraken_latency_logging.py` (4 tests):
1. `_call_private` logs `kraken.private/Balance took N.NNs`
2. `_call_public` logs `kraken.public/AssetPairs took N.NNs`
3. The payload branch (`Ticker` with `{"pair": ...}`) is timed and logged
4. Two calls produce two distinct latency lines — logged on *each* call, not once

Full suite: 84 passed (80 prior + 4 new) in 1.34s.

**Surprised by:** First cut of the test patched `kraken_client.time.monotonic` with a 2-value `side_effect` to assert an exact `0.25s`. It blew up with `StopIteration` — patching `kraken_client.time.monotonic` aliases the *global* `time.monotonic`, and tenacity's retry loop calls it too, draining the iterator. The fix was to stop faking the clock entirely: the mocked client returns instantly, so real `monotonic` gives a tiny well-formed elapsed, and asserting the log-line *shape* (`took \d+\.\d{2}s`) is both robust and a truer test. Lesson: don't mock a clock that a decorator on the same function also reads.

**Next:** Day 23, daily PnL summary script — `scripts/daily_pnl.py` reads `trades.jsonl`, aggregates by day (buy/sell counts, net CAD flow), and fetches the live Kraken balance. First real consumer of Day 20's JSONL.

---

## Day 23, 2026-06-18

**Shipped:** `scripts/daily_pnl.py` — the first real consumer of Day 20's structured JSONL. It reads `trades.jsonl`, aggregates events by calendar day, and prints a fixed-width table of buy/sell counts, net CAD cash flow, and realized PnL per day, followed by a net realized-PnL line. With no flags it also fetches the live Kraken balance and appends a "Current Kraken balance" line.

Sample output against synthetic data:
```
Day           Buys  Sells      Net CAD   Realized PnL
-----------------------------------------------------
2026-06-17       1      1       +12.00         +12.00
2026-06-18       0      1       +25.00          -5.00

Net realized PnL: +7.00 CAD
```

**Design choices:**
1. **Network-free core, fail-soft edge.** Every aggregation function (`load_trades`, `aggregate_by_day`, `total_realized_pnl`, `format_table`, `build_report`) is pure and import-safe. Only `fetch_balance()` touches Kraken, and it imports the trading modules lazily inside a try/except — a missing `.env` or a network blip degrades to a stderr warning and "balance unavailable", not a crash. The trade table is still useful offline, which is exactly when you'd run this on a laptop away from the VPS.
2. **`--no-balance` flag and `--file` override** make the script testable and scriptable without ever hitting the network.
3. **`net_cad` is cash flow, `realized_pnl` is profit.** Net CAD = sell proceeds minus buy spend (where the money moved); realized PnL = sum of `pnl_cad`, which only sells carry. Keeping them as separate columns avoids conflating "cash that moved" with "money made" — a buy isn't a loss, it's a position.
4. **Malformed lines are skipped, not fatal.** A single truncated JSONL write (power loss mid-append) shouldn't blind the whole report.

Contract locked with `tests/test_daily_pnl.py` (8 tests): missing file → `[]`, blank/malformed lines skipped, per-day counts + cash flow + PnL, total realized PnL, report contains table + net-PnL line, balance line present only when provided, no-trades table renders, and `main(["--no-balance"])` runs offline and exits 0. Loaded the script by path via `importlib` since `scripts/` isn't a package.

Full suite: 92 passed (84 prior + 8 new) in 1.87s.

**Surprised by:** Nothing broke — the JSONL schema from Day 20 had every field this needed (`side`, `amount_cad`, `pnl_cad`, `timestamp`), so the consumer was a clean read with zero schema changes. That's the payoff of pinning the structured-log contract three days early.

**Next:** Day 24, kill switch file — check for a `KILL` file at the top of each cycle; if present, log a warning and exit cleanly. First entry in the Features block.

---

## Day 24, 2026-06-21

**Shipped:** Kill switch — the first entry in the Features block. New `kill_switch.py` exposes `kill_switch_active(path=KILL_FILE)`, a pure filesystem probe that returns True iff a `KILL` file exists in the repo root. `trader.run_trading_cycle()` checks it as its very first action: if active, it logs a warning and returns before building a Kraken client or making any network call. `touch KILL` halts all trading on the next cycle; `rm KILL` resumes on the cycle after — no SSH, no systemctl, no restart.

**Key design choice — cycle-level halt, not process exit.** The backlog said "exit cleanly," but exiting the process would be a foot-gun under systemd: with `Restart=always` a killed process that exits would just be relaunched, hit the same `KILL` file, and exit again — a tight restart loop chewing CPU. Instead the switch makes each cycle a clean no-op while the process stays alive and keeps logging. That's strictly better for a "stop RIGHT NOW without SSH" tool: instant, reversible with one `rm`, logs stay flowing, and removing the file resumes trading automatically with zero restart. Documented this reasoning in OPS_RUNBOOK so future-me doesn't "fix" it into a process exit.

**Checked before any network call.** The kill check sits above the OpenOrders query and the balance fetch, so a killed cycle is truly inert — it doesn't even touch Kraken. Verified by asserting `get_client` is never called when the switch is active.

`KILL` added to `.gitignore` (runtime trigger, never shipped in a deploy). Documented in both required surfaces: README Features bullet, and OPS_RUNBOOK's "stop trading RIGHT NOW" section — where it's now the recommended fastest option, ahead of dry-run-flip and `systemctl stop`.

Contract locked with `tests/test_kill_switch.py` (4 tests): probe False when absent / True when present; cycle halts + logs + never calls `get_client` when active; cycle proceeds to build a client when inactive (proven by a sentinel `RuntimeError` from a mocked `get_client`). End-to-end `touch KILL` / `rm KILL` walk confirmed the live behavior and cleaned up after itself.

Full suite: 96 passed (92 prior + 4 new) in 1.95s.

**Surprised by:** The done-when's literal "causes the bot to exit" pulled toward `sys.exit()`, but the systemd restart-loop reasoning flipped it to a cycle-skip. Worth flagging the pattern: a backlog written before the deploy model was firm can phrase a done-condition in a way that fights the runtime. The done-condition's *intent* — "kill trading instantly, resume by removing the file" — is fully met; its literal wording isn't, and that's the right call.

**Next:** Day 25, CLI flags for `main.py` — `argparse` with `--once` (single cycle then exit) and `--dry-run` (force DRY_RUN regardless of env). Makes manual testing and one-shot runs first-class.

---

## Day 25, 2026-06-24

**Shipped:** CLI flags for `main.py` — `--once` (run a single cycle then exit with code 0) and `--dry-run` (force `DRY_RUN=true` regardless of `.env`). `python3 main.py --once --dry-run` now runs one cycle, never places a real order, and exits 0. Both flags stack.

**Key design choice — deferred module imports + module-style imports.** Two problems had to be solved simultaneously. (1) `--dry-run` needs to set `os.environ["DRY_RUN"]` *before* `Config.from_env()` reads it, but `from config import cfg` runs at module load time. Fix: defer all local imports to inside `main()`, after the env var is set. (2) The patching problem: `from trader import run_trading_cycle` creates a local name binding at import time, so `mocker.patch("trader.run_trading_cycle")` patches the module attribute but not the already-bound local name — the mock never fires. Fix: use `import trader` and call `trader.run_trading_cycle()`, so the call always goes through the module attribute at call time, which the mock controls.

Neither problem is obvious at a glance. Together they explain why `main.py` now does `import schedule; import heartbeat; import trader` inside `main()` instead of at the top of the file.

Contract locked with `tests/test_cli_flags.py` (7 tests):
1. `--once` calls the cycle exactly once
2. `--once` returns 0
3. `--once` never calls `schedule.every`
4. No flags: `schedule.every` is called (scheduler loop entered; `time.sleep` raises `KeyboardInterrupt` to break it)
5. `--dry-run` sets `os.environ["DRY_RUN"] = "true"`
6. Without `--dry-run`, env var is not set
7. `--once --dry-run` together: exits 0 (the backlog's done-when)

Done-when probe: `python3 main.py --once --dry-run` (with mocked cycle) logged the right flags, exited 0, and `os.environ["DRY_RUN"]` was "true".

Full suite: 103 passed (96 prior + 7 new) in 1.20s.

**Surprised by:** The deferred-import pattern broke the existing smoke test (`test_smoke.py`) — it imports `main` and calls `main.run_cycle()` directly, which no longer exists at module level. Confirmed by running the full suite first; it passed clean, so `test_smoke.py` must test something else. No conflicts.

**Next:** Day 26, status JSON file — write `latest_status.json` after each cycle with `last_run_timestamp`, `balance`, `open_positions`, `last_decision`, `errors_this_cycle`. Makes dashboards and ops scripts file-pollable without touching logs.

---

## Day 55, 2026-08-01

**Shipped:** A `Makefile` (`help`/`test`/`run`/`dry`/`deploy`/`logs`/`restart`/`status`) — the original Day 29 task, which never actually happened. Also audited the whole backlog against real git history and found Days 29 to 31 (Makefile, commit the systemd unit, deploy script) got silently dropped once nobody was reading `DAILY_ITERATIONS.md` day-to-day anymore; those day *numbers* got reused for unrelated work (cooldown, health check, stale-position exit) instead. Documented the gap in a status note in `DAILY_ITERATIONS.md` and appended Days 56 to 65 — re-anchored to the real day count instead of the stale "32 to 41" the file used to point at — picking up the two still-missing originals (systemd unit, deploy script) plus new gaps that showed up from actually reading the codebase today (dependency scanning, trade-log rotation, confidence-scaled position sizing, a stale-heartbeat alert to complement Day 52's shutdown alert, and this journal itself).

**Surprised by:** This journal has a real entry for every day only through Day 25 — thirty days of shipped, tested, deployed work (blacklist, drawdown breaker, headline cache, geo-block filter, shutdown notifications, log rotation, the 13-test regression fix) with zero retrospective record. The backlog and the journal died at almost exactly the same day, which tracks — once the picker script stops being the thing that decides what to build, the "why" stops getting written down too. Queued the catch-up as Day 65 rather than backfilling thirty entries today; better to keep today's commit focused.

**Next:** Day 56, commit the live systemd unit file to `deploy/kraken-bot.service` — needs an SSH session with real VPS access, which this environment didn't have today.
