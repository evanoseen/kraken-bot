# Operations Runbook

This bot trades real CAD on a live Kraken account from a Hetzner VPS. When something looks wrong, this file is the first place to look. Every section is concrete commands you can paste, not descriptions.

> **Quick reference card**
> - **Server:** `root@204.168.204.221` (Hetzner CX23, Ubuntu 24.04)
> - **Service:** `kraken-bot.service` (systemd, `Restart=always`)
> - **Server path:** `/root/kraken-bot/`
> - **Local path:** `/Users/evanoseen/kraken-bot/`
> - **Live config:** `/root/kraken-bot/.env` on the server (NEVER committed)
> - **Live trading toggle:** `DRY_RUN=false` in `.env`

---

## 1. SSH access

### Connect to the server

```bash
ssh root@204.168.204.221
```

The Hetzner CX23 runs Ubuntu 24.04. The bot lives at `/root/kraken-bot/` and runs as root under systemd.

### One-shot remote commands (no full shell)

```bash
ssh root@204.168.204.221 'systemctl status kraken-bot --no-pager'
ssh root@204.168.204.221 'journalctl -u kraken-bot -n 50 --no-pager'
ssh root@204.168.204.221 'cat /root/kraken-bot/positions.json'
ssh root@204.168.204.221 'tail -50 /root/kraken-bot/bot.log'
```

### If SSH fails

```bash
# 1. Verify the VPS is up
ping -c 3 204.168.204.221

# 2. Check the Hetzner console at hetzner.cloud (reset / VNC / power-cycle)
#    Account holder: Evan. Project: cyber-tools.

# 3. If ping works but SSH does not, the SSH daemon may be wedged.
#    Use the Hetzner console to log in and run:
systemctl restart sshd
```

---

## 2. Systemd commands

The bot runs as a single systemd unit: `kraken-bot.service`. Unit file lives at `/etc/systemd/system/kraken-bot.service` on the server.

### Status

```bash
# Is the bot running right now?
systemctl status kraken-bot --no-pager

# Active / inactive / failed in one line
systemctl is-active kraken-bot

# Enabled at boot?
systemctl is-enabled kraken-bot
```

### Lifecycle

```bash
systemctl start kraken-bot     # start a stopped bot
systemctl stop kraken-bot      # stop the bot
systemctl restart kraken-bot   # graceful: stop + start
systemctl reload kraken-bot    # NOT supported — use restart

# Disable autostart on reboot (keeps the bot stopped after server reboots)
systemctl disable kraken-bot

# Re-enable autostart
systemctl enable kraken-bot
```

### After editing the unit file

```bash
# Edit
nano /etc/systemd/system/kraken-bot.service

# Reload systemd's view of unit files
systemctl daemon-reload

# Apply changes
systemctl restart kraken-bot
```

---

## 3. Log inspection

The bot writes to two places: systemd's journal (everything stdout sees) and `bot.log` on disk (configured in `main.py`).

### journalctl — the systemd journal

```bash
# Tail the last 50 lines (most common command)
journalctl -u kraken-bot -n 50 --no-pager

# Live-follow new log lines (Ctrl-C to exit)
journalctl -u kraken-bot -f

# Last 30 minutes
journalctl -u kraken-bot --since "30 min ago" --no-pager

# Errors and warnings only
journalctl -u kraken-bot -p warning --no-pager

# A specific day
journalctl -u kraken-bot --since "2026-05-25 00:00" --until "2026-05-25 23:59" --no-pager
```

### bot.log — the file logger

```bash
# Tail the last 50 lines
tail -n 50 /root/kraken-bot/bot.log

# Live-follow
tail -f /root/kraken-bot/bot.log

# Grep for trade activity
grep -E "STOP-LOSS|TAKE-PROFIT|Order placed" /root/kraken-bot/bot.log

# Grep for errors
grep -E "ERROR|error" /root/kraken-bot/bot.log | tail -n 50
```

### State files

```bash
ls -la /root/kraken-bot/
# Files of interest:
#   positions.json       — currently held buys (entry_price, amount_cad, timestamp)
#   seen_listings.json   — listing IDs already actioned (de-dup)
#   trades.csv           — append-only trade history
#   bot.log              — full log
#   .env                 — secrets and tunables (NEVER commit)

cat positions.json     # current open positions
tail -n 20 trades.csv  # recent trades
```

### Trade log archiving (Day 59)

`trades.csv` and `trades.jsonl` are append-only forever — same problem `bot.log` had before Day 54 rotated it, just slower growing since a trade is rarer than a log line. `scripts/archive_trades.py` splits entries older than N days (default 90) into a dated archive pair (`trades_archive_<cutoff-date>.csv/.jsonl`) next to the live files, rewriting the live files atomically so a crash mid-run can't corrupt them.

```bash
# Preview what would move, without writing anything
ssh root@204.168.204.221 'cd /root/kraken-bot && venv/bin/python3 scripts/archive_trades.py --dry-run'

# Actually archive entries older than 90 days (the default)
ssh root@204.168.204.221 'cd /root/kraken-bot && venv/bin/python3 scripts/archive_trades.py'

# Custom cutoff
ssh root@204.168.204.221 'cd /root/kraken-bot && venv/bin/python3 scripts/archive_trades.py --days 30'
```

**Suggested monthly cron** (run on the VPS, first of the month, well outside market-open hours doesn't matter here since it never touches Kraken):
```cron
0 3 1 * * cd /root/kraken-bot && venv/bin/python3 scripts/archive_trades.py >> /root/kraken-bot/archive_trades.log 2>&1
```
Install with `ssh root@204.168.204.221 'crontab -e'` and paste the line above. The script is idempotent and network-free — a missed or double-run month is harmless.

---

## 4. Deploy procedure

The local source of truth is `/Users/evanoseen/kraken-bot/` on Evan's Mac. The VPS copy is downstream — it gets overwritten.

### Standard deploy (Day 57)

```bash
make deploy
# or directly:
./scripts/deploy.sh
```

This runs the test suite, rsyncs the repo to the VPS (`.env`, `.git`, `venv`, and `__pycache__` excluded so the live secrets file is never clobbered), restarts `kraken-bot.service`, then polls the Day 21 heartbeat file (`last_run.txt`) for up to 3 minutes until it advances past its pre-deploy value. Fails loudly and exits non-zero at whichever step breaks — tests, rsync, restart, or a heartbeat that never advances (the strongest signal the restart actually broke something, not just that `systemctl restart` returned 0).

Healthy startup in the tailed logs looks like:
```
"Kraken Meme Coin NewsTrader starting..."
"Running every N minutes"
"Balance: $X.XX CAD"
```

### Manual deploy (fallback, if `scripts/deploy.sh` itself is broken)

```bash
# 1. From local repo root, push to the VPS — rsync, not scp, so .env is never clobbered
rsync -av --exclude='.env' --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  /Users/evanoseen/kraken-bot/ root@204.168.204.221:/root/kraken-bot/

# 2. SSH in and restart the service
ssh root@204.168.204.221 'systemctl restart kraken-bot'

# 3. Tail logs to confirm the bot came back cleanly
ssh root@204.168.204.221 'journalctl -u kraken-bot -n 30 --no-pager'
```

If you ever fall back to `scp -r` instead of `rsync`, back up `.env` first — `scp -r` of the whole directory **will** clobber it:
```bash
ssh root@204.168.204.221 'cp /root/kraken-bot/.env /root/kraken-bot/.env.bak'
scp -r /Users/evanoseen/kraken-bot root@204.168.204.221:/root/
ssh root@204.168.204.221 'mv /root/kraken-bot/.env.bak /root/kraken-bot/.env'
```

### Pre-deploy checklist (do this every time)

1. `DRY_RUN=true` locally for a full cycle and watched the logs.
2. No uncommitted secrets in any file about to be synced.
3. Confirm the service restarted with `systemctl status` showing `active (running)` (or trust `scripts/deploy.sh`'s heartbeat check, which verifies the same thing more precisely).

---

## 5. Rollback procedure

When a deploy breaks the bot, get back to a known-good state fast.

### Option A — Roll back via git (preferred)

```bash
# 1. Locally, identify the last known-good commit
git log --oneline -10

# 2. Check it out into a temp worktree (does not disturb your main branch)
git worktree add /tmp/kraken-rollback <commit-sha>

# 3. Deploy the rollback (rsync to avoid clobbering .env)
rsync -av --exclude='.env' --exclude='.git' /tmp/kraken-rollback/ root@204.168.204.221:/root/kraken-bot/

# 4. Restart and verify
ssh root@204.168.204.221 'systemctl restart kraken-bot && journalctl -u kraken-bot -n 30 --no-pager'

# 5. Clean up
git worktree remove /tmp/kraken-rollback
```

### Option B — In-place revert on the server (faster but uglier)

```bash
ssh root@204.168.204.221
cd /root/kraken-bot
# If the broken deploy was the only change since last working state:
git stash       # if a .git lives on the server; otherwise re-deploy from local
# Otherwise re-deploy from a local known-good commit as in Option A.
```

### Option C — Emergency stop (no rollback yet, just halt)

```bash
ssh root@204.168.204.221 'systemctl stop kraken-bot && systemctl disable kraken-bot'

# Bot is now down and will NOT auto-restart on next boot. Re-enable later with:
ssh root@204.168.204.221 'systemctl enable kraken-bot && systemctl start kraken-bot'
```

### After any rollback

- Watch `journalctl -u kraken-bot -f` for two full cycles (about 30 min at default `RUN_INTERVAL_MINUTES=15`).
- Verify `positions.json` still reflects reality. If a trade landed mid-deploy and the rollback lost it, manually edit the file.
- Note the incident in `JOURNAL.md` so the cause is captured.

---

## 6. Triage — "the bot is misbehaving"

Work top to bottom. The questions get less obvious; the first one that triggers is the answer.

### Symptom: no trades for hours

```bash
# 1. Is the bot even running?
ssh root@204.168.204.221 'systemctl is-active kraken-bot'
# expected: active

# 2. Are cycles running?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since "30 min ago" --no-pager | grep "Starting trading cycle"'
# expected: at least one line in the last RUN_INTERVAL_MINUTES window

# 3. Did the daily loss limit trip?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since today --no-pager | grep "Daily loss limit"'
# if YES: the bot is correctly halted for the day. Wait or restart in DRY_RUN to bypass.

# 4. Is balance under $5?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since "1 hour ago" --no-pager | grep "Insufficient balance"'

# 5. Are signals being generated but filtered?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since "1 hour ago" --no-pager | grep -E "Found .* signal|No confident signals"'

# 6. Is Claude failing?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since "1 hour ago" --no-pager | grep "Error in analysis"'
```

### Symptom: bot is in failed state

```bash
ssh root@204.168.204.221 'systemctl status kraken-bot --no-pager'

# Look at the most recent stderr / stdout:
ssh root@204.168.204.221 'journalctl -u kraken-bot -n 100 --no-pager | tail -n 100'

# Common causes:
#   ModuleNotFoundError  -> dependency missing, run pip install -r requirements.txt
#   PermissionError      -> .env or a state file lost its permissions; chmod 600 .env
#   KrakenError 'EAPI'   -> API key issue, check .env on server
#   ConnectionError      -> DNS / network, check the VPS itself
```

### Symptom: Kraken API errors

```bash
# How frequent?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since today --no-pager | grep -c "error"'

# What kind?
ssh root@204.168.204.221 'journalctl -u kraken-bot --since today --no-pager | grep -E "Balance error|AssetPairs error|Order error" | tail -n 30'

# If it's "EAPI:Rate limit" → throttled. Day 18-19 backlog items add retry + rate limiter.
#   Short-term fix: increase RUN_INTERVAL_MINUTES in .env, restart.

# If it's "EAPI:Invalid key" → API key expired / rotated. Re-set in .env.

# If it's "EService:Unavailable" → Kraken itself is down. Wait it out.
```

### Symptom: positions look wrong

```bash
# Compare what the bot thinks it holds vs what Kraken reports
ssh root@204.168.204.221 'cat /root/kraken-bot/positions.json'

# Then check Kraken's view via the API:
ssh root@204.168.204.221 'cd /root/kraken-bot && /root/kraken-bot/venv/bin/python -c "from kraken_client import get_client, get_holdings; print(get_holdings(get_client()))"'

# Reconcile by editing positions.json directly if the bot's view diverged
# (e.g. after a manual trade on the Kraken web UI, the bot's positions.json will not know about it).
```

### Symptom: I want to stop trading RIGHT NOW

```bash
# Fastest (no restart): drop the kill-switch file. The next cycle becomes a
# no-op — no network calls, no orders — and logs a clear warning. Day 24.
ssh root@204.168.204.221 'touch /root/kraken-bot/KILL'

# Confirm it took effect (look for the warning on the next cycle)
ssh root@204.168.204.221 'journalctl -u kraken-bot -n 20 --no-pager | grep "KILL switch"'

# Resume trading — just remove the file. No restart needed; next cycle runs normally.
ssh root@204.168.204.221 'rm -f /root/kraken-bot/KILL'

# Alternative: flip dry-run on the server, restart (keeps cycles fully running)
ssh root@204.168.204.221 'sed -i "s/^DRY_RUN=.*/DRY_RUN=true/" /root/kraken-bot/.env && systemctl restart kraken-bot'
# Bot keeps running but does not place orders. Logs still flow so you can see what
# it WOULD have done.
```

The kill switch beats both dry-run and `systemctl stop`: it's instant, needs no
restart, leaves the process and its logs alive, and reverses with a single `rm`.
The `KILL` file is git-ignored so it never ships in a deploy.

### Symptom: I want to halt fully

```bash
ssh root@204.168.204.221 'systemctl stop kraken-bot && systemctl disable kraken-bot'
```

---

## 7. Files on the server

A quick map so you do not have to remember.

```
/root/kraken-bot/
├── main.py                 # entry point under systemd
├── trader.py               # cycle orchestrator
├── kraken_client.py        # Kraken REST wrapper
├── market_matcher.py       # Claude news signal extractor
├── news_fetcher.py         # RSS + Nitter fetch
├── pump_detector.py        # obscure-pump scanner
├── listing_monitor.py      # Kraken blog listing watch
├── positions.py            # position state (positions.json)
├── config.py               # .env loader
├── requirements.txt        # pip deps
├── venv/                   # virtualenv
├── .env                    # secrets and tunables — DO NOT COMMIT
├── positions.json          # open positions (auto-managed)
├── seen_listings.json      # listing IDs already actioned
├── trades.csv              # trade history (append-only)
└── bot.log                 # local logger output

/etc/systemd/system/
└── kraken-bot.service      # systemd unit (Day 30 backlog: commit a copy to deploy/)
```

---

## 8. Environment variables

The full env contract lives in `config.py`. Quick reference:

| Variable | Purpose | Live default |
|----------|---------|--------------|
| `KRAKEN_API_KEY` | Kraken REST key (trade-enabled) | secret |
| `KRAKEN_PRIVATE_KEY` | Kraken REST private key | secret |
| `ANTHROPIC_API_KEY` | Claude API key (for `market_matcher`) | secret |
| `MAX_TRADE_AMOUNT` | CAD cap per trade before confidence scaling | `40.0` |
| `MIN_CONFIDENCE` | Filter floor for news signals | `0.65` |
| `RUN_INTERVAL_MINUTES` | Cycle cadence | `5` |
| `DAILY_LOSS_LIMIT` | CAD daily session stop | `100.0` |
| `STOP_LOSS_PCT` | Per-position stop loss (fraction) | `0.10` |
| `TAKE_PROFIT_PCT` | Per-position take profit (fraction) | `0.25` |
| `DRY_RUN` | Master live-trading toggle | `false` (live) |

### Inspect live env

```bash
ssh root@204.168.204.221 'cat /root/kraken-bot/.env'
```

### Change a tunable in flight

```bash
# Example: lower MAX_TRADE_AMOUNT to 20.0 CAD
ssh root@204.168.204.221 'sed -i "s/^MAX_TRADE_AMOUNT=.*/MAX_TRADE_AMOUNT=20.0/" /root/kraken-bot/.env && systemctl restart kraken-bot'
```

---

## 9. Verification after any change

Always run this trio after a deploy, rollback, env edit, or restart:

```bash
ssh root@204.168.204.221 << 'EOF'
echo "=== service ==="
systemctl is-active kraken-bot
echo "=== last 30 log lines ==="
journalctl -u kraken-bot -n 30 --no-pager
echo "=== positions ==="
cat /root/kraken-bot/positions.json 2>/dev/null || echo "(no positions file yet)"
echo "=== last 5 trades ==="
tail -n 5 /root/kraken-bot/trades.csv 2>/dev/null || echo "(no trades file yet)"
EOF
```

Healthy output: `active`, recent "Starting trading cycle" or "Trading cycle complete" lines, no unhandled exceptions in the tail.
