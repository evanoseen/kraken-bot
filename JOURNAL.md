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

**Surprised by:** The Anthropic SDK validates `api_key` at constructor time, not at first-request time. That meant the CI workflow had to fake an env var even though zero real API calls happen during tests. Saved a debugging cycle by setting it preemptively.

**Next:** Day 14, replace every `print()` in the trading modules with a proper `logging` call; the root logger config moves into `main.py`.
