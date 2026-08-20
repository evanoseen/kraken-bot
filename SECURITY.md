# Security

This bot trades real CAD on a Kraken account from a single Hetzner VPS. The blast radius of a compromise is bounded by the per-trade and daily-loss caps in `config.py`, but the API keys themselves can fund-withdraw if their permissions are too broad. This document is the working threat model and the operator checklist that hardens against it.

> Reporting: if you find a vulnerability in this code, open a private issue at
> <https://github.com/evanoseen/kraken-bot/issues/new> with the `security` label,
> or email evan.e.oseen@gmail.com. Do not file a public report.

---

## 1. API key storage

### Threat
- Keys committed to git, ever, even briefly. GitHub indexes pushed commits within minutes; secret scanners harvest them before you can rotate.
- Keys readable by other processes on the VPS.
- Keys leaked through verbose logging (`logger.info(.env contents)`, accidental tracebacks that include request payloads).

### Posture
- All secrets live in `.env` on the VPS only. `.env` is listed in `.gitignore` and verified before each commit by the daily workflow.
- `.env.example` ships placeholder strings so a new clone never sees a real key.
- Kraken API keys are scoped to the minimum permissions the bot actually uses: **Query Funds**, **Query Open Orders**, **Modify Orders**, **Create / Cancel Orders**. Withdrawal permissions are **off**.
- The Anthropic key is per-project and rate-limited at the org level.

### Concrete actions
```bash
# 1. Confirm .gitignore still excludes .env
ssh root@204.168.204.221 'grep -E "^\.env$" /root/kraken-bot/.gitignore' || echo "FAIL"

# 2. Lock down .env file permissions
ssh root@204.168.204.221 'chmod 600 /root/kraken-bot/.env && ls -la /root/kraken-bot/.env'
# expected: -rw------- 1 root root ... .env

# 3. Audit the git history for any accidental commits
git log -p --all | grep -E "KRAKEN_(API|PRIVATE)_KEY=[A-Za-z0-9+/=]{20,}|ANTHROPIC_API_KEY=sk-ant-" \
  && echo "FAIL — key found in history, rotate immediately" \
  || echo "clean"

# 4. Confirm Kraken key permissions in the dashboard
#    https://www.kraken.com/u/security/api -> review the key used by this bot
#    Required: Query Funds, Query Open Orders, Modify Orders, Create/Cancel Orders
#    Forbidden: Withdrawal of Funds
```

---

## 2. Key rotation

### Threat
- A long-lived key that has touched any compromised surface (a leaked log, a stolen laptop, a careless paste) is silently weaponized.
- Rotation that takes the bot offline for hours creates pressure to skip it.

### Posture
- Rotate Kraken keys **quarterly** and immediately after any suspected leak (laptop loss, malware scare, accidental commit even if force-pushed away).
- Rotate the Anthropic key **annually** or on suspected leak.
- Rotation is a two-key window: create the new key, swap `.env`, restart, then disable the old key once two full cycles complete cleanly.

### Concrete actions
```bash
# 1. In the Kraken dashboard, create a NEW key with the same minimum permissions
#    (Query Funds, Query Open Orders, Modify Orders, Create/Cancel Orders).
#    Note the new public/private pair.

# 2. Stage the new key on the server
ssh root@204.168.204.221 << 'EOF'
cp /root/kraken-bot/.env /root/kraken-bot/.env.bak.$(date +%Y%m%d)
sed -i 's/^KRAKEN_API_KEY=.*/KRAKEN_API_KEY=NEW_PUBLIC_KEY_HERE/' /root/kraken-bot/.env
sed -i 's/^KRAKEN_PRIVATE_KEY=.*/KRAKEN_PRIVATE_KEY=NEW_PRIVATE_KEY_HERE/' /root/kraken-bot/.env
chmod 600 /root/kraken-bot/.env
systemctl restart kraken-bot
EOF

# 3. Watch two full cycles in journalctl to confirm the new key works
ssh root@204.168.204.221 'journalctl -u kraken-bot -n 60 --no-pager -f'
#    Look for: "Balance: $X.XX CAD" with no "EAPI:Invalid key" errors.

# 4. Once verified, delete the OLD key in the Kraken dashboard.
#    Same flow for ANTHROPIC_API_KEY via https://console.anthropic.com/.

# 5. Delete the .env.bak.YYYYMMDD file after verification.
ssh root@204.168.204.221 'shred -u /root/kraken-bot/.env.bak.*'
```

---

## 3. Kill switch design

### Threat
- A buggy signal source or runaway feedback loop drains the account between cycles. `systemctl stop` requires SSH, which costs seconds that a degenerate loop will eat.
- An attacker with shell access could re-enable the bot before you notice.

### Posture (current)
Three halt mechanisms exist today:
1. **`KILL` file in the repo root** (Day 24) — the trader checks for it at the top of each cycle and exits cleanly if present. No SSH-and-systemctl race. `touch KILL` from anywhere with file access stops the bot within one cycle; `rm KILL` resumes it.
2. **`DRY_RUN=true`** in `.env` then `systemctl restart kraken-bot`. Bot keeps cycling but places no orders. Use this when you want to keep observing behavior.
3. **`systemctl stop kraken-bot && systemctl disable kraken-bot`**. Bot is gone until you re-enable it. Use this for real incidents.

The **`DAILY_LOSS_LIMIT`** and **`MAX_DRAWDOWN_PCT`** (Day 27) in `config.py` are soft kills: when session loss or drawdown exceeds the configured threshold, the bot halts trading for the rest of the session.

### Concrete actions
```bash
# Fastest kill switch — no SSH needed if you already have a shell on the box
ssh root@204.168.204.221 'touch /root/kraken-bot/KILL'
# Resume: ssh root@204.168.204.221 'rm /root/kraken-bot/KILL'

# Dry-run kill switch
ssh root@204.168.204.221 'sed -i "s/^DRY_RUN=.*/DRY_RUN=true/" /root/kraken-bot/.env && systemctl restart kraken-bot'
# Bot now logs decisions but does not place orders.

# Full halt
ssh root@204.168.204.221 'systemctl stop kraken-bot && systemctl disable kraken-bot'

# Verify halt
ssh root@204.168.204.221 'systemctl is-active kraken-bot'
# expected: inactive
```

---

## 4. Network exposure of the VPS

### Threat
- Open SSH on a default port with password authentication invites brute force.
- A compromised VPS leaks `.env` regardless of how careful the repo workflow is.
- Outbound DNS to a hostile resolver intercepts API calls.

### Posture
- The Hetzner CX23 exposes **only port 22 (SSH)** to the internet. Bot makes only outbound HTTPS to Kraken, Anthropic, and RSS sources.
- SSH is **public-key only**; password auth disabled in `/etc/ssh/sshd_config` (`PasswordAuthentication no`).
- Root login is permitted but only via key. (Future hardening: create a non-root user, sudo for systemd ops, disable direct root SSH.)
- No reverse shell, no Telegram bot listener inbound, no web UI.

### Concrete actions
```bash
# 1. Audit open ports from outside (run from your laptop, not the VPS)
nmap -Pn 204.168.204.221
# expected: only port 22 (ssh) open

# 2. Confirm password auth is off
ssh root@204.168.204.221 'grep -E "^(PasswordAuthentication|PermitRootLogin|PubkeyAuthentication)" /etc/ssh/sshd_config'
# expected:
#   PasswordAuthentication no
#   PubkeyAuthentication yes
#   PermitRootLogin prohibit-password   (or "without-password")

# 3. Review recent SSH attempts
ssh root@204.168.204.221 'journalctl -u ssh --since "24 hours ago" --no-pager | grep -E "Failed|Accepted" | tail -n 50'
# Investigate any "Failed password" lines from unknown IPs.

# 4. Hetzner cloud firewall (optional, belt-and-suspenders):
#    https://console.hetzner.cloud -> Firewalls -> attach to this VPS
#    Allow: inbound TCP 22 only. Block all other inbound.
```

---

## 5. Dependency vulnerability policy

### Threat
- A compromised PyPI package (krakenex, anthropic, feedparser, schedule, python-dotenv, requests) executes arbitrary code under root on the VPS.
- A typosquatted name (`kraken-ex`, `anthopic`) is installed instead of the real package.
- Stale deps accumulate known CVEs.

### Posture
- Dependencies are pinned in `requirements.txt`. Upgrades happen deliberately, not via `pip install --upgrade`.
- Before any dep upgrade: read the changelog, scan the diff for unusual additions (new network endpoints, new file writes, new subprocess calls).
- **`pip-audit` runs in CI on every push and pull request** (Day 58, `.github/workflows/test.yml`) — a known CVE in any pinned dependency fails the build instead of waiting for a monthly manual run to catch it.
- Treat ANY new transitive dependency as a code review surface.

### Remediation when the CI scan fails
1. Read the `pip-audit` output — it names the vulnerable package, the installed version, the CVE/GHSA ID, and the first fixed version.
2. **Verify the fix version actually exists** with `pip index versions <package>` before assuming it's a one-line bump — on Day 58 (2026-08-04), all 8 findings in this repo's dependency tree named a fix version that isn't published on PyPI (confirmed with a freshly-upgraded pip against the real index, not a caching artifact), meaning there was nothing to upgrade to.
3. If a real fix version exists: bump that one dependency in `requirements.txt` to it. Don't bump unrelated deps in the same commit. Run `pip install -r requirements.txt && pytest -v && pip-audit -r requirements.txt` locally to confirm the fix and that nothing else broke. Commit with a message naming the CVE (`git commit -m "Bump requests to 2.32.6 (PYSEC-2026-2275)"`) so the fix is searchable in history.
4. If no fixed version exists yet: check whether the vulnerable code path is even reachable by this bot (e.g., a vuln in an HTTP server component of a library only used as a client). Add `--ignore-vuln <ID>` to the CI step (`.github/workflows/test.yml`) with a one-line comment reason, and log it in the table below. Re-check `pip index versions` for that package at the next audit — once a fix ships, remove the ignore and bump.
5. Never widen an ignore to a whole package or a version range — one `--ignore-vuln <ID>` per advisory, so a *different* future CVE in the same package still fails the build.

### Currently ignored (no fix published yet — checked 2026-08-04)

| ID | Package | Installed | Reachable from this bot? | Revisit |
|----|---------|-----------|---------------------------|---------|
| PYSEC-2026-2275 | requests | 2.32.5 | Yes — direct runtime dep (Kraken/Telegram/Anthropic HTTP calls) | Every audit |
| PYSEC-2026-142, PYSEC-2026-141 | urllib3 | 2.6.3 | Transitive via `requests` | Every audit |
| PYSEC-2026-2270 | python-dotenv | 1.2.1 | Yes — loads `.env`, never parses untrusted input | Every audit |
| PYSEC-2026-1845 | pytest | 8.4.2 | No — test-only, never runs on the VPS | Every audit |
| GHSA-6v7p-g79w-8964 | msgpack | 1.1.2 | No — transitive via `pip-audit`'s own CI-only dependency (`CacheControl`), not installed on the VPS | Every audit |
| PYSEC-2026-1375, PYSEC-2026-1374 | filelock | 3.19.1 | No — transitive via `pip-audit`, CI-only | Every audit |

`requests` and `python-dotenv` are the two that matter for the live bot; both are already pinned to `>=` their latest available version, so there's nothing more to do until upstream ships an actual fix.

### Upper-bound pins (Day 71)

Before Day 71, every line in `requirements.txt` was `package>=X.Y.Z` with no ceiling — a fresh install (a new machine, a rebuilt VPS, CI's own `pip install`) could silently pull a breaking major-version bump with zero warning, even though this section already said to read the changelog before any upgrade. The policy existed; nothing enforced it on first install. That's now fixed: every line has both a lower and an upper bound.

**Bound convention:** one major version above whatever's currently installed (`package>=X.Y.Z,<(X+1).0.0`) — except pre-1.0 packages (currently only `anthropic`, at `0.105.2`), which get bounded at the next **minor** instead (`<0.106.0`), since SemVer treats any `0.x` release as potentially breaking, not just a major bump. `types-requests` is bounded to match `requests`' major, since its version scheme mirrors the package it stubs.

**Bump procedure** — one dependency per commit, never batch:
```bash
# 1. Check what's actually available before editing anything
pip index versions <package>

# 2. Bump ONLY that package's version bounds in requirements.txt
#    (lower bound to the new version, or leave it — upper bound per the
#    convention above if you're also crossing a major/minor boundary)

# 3. Reinstall and verify
pip install -r requirements.txt
make test

# 4. Commit with the package and version in the message
git commit -m "Bump requests to 2.33.0"
```
If `make test` fails after a bump, that's the changelog-reading step this policy has always asked for, just enforced by the test suite instead of trusted to memory — read what changed, decide whether it's a real break or a test that needs updating, and fix accordingly before committing.

### Concrete actions
```bash
# 1. Install pip-audit if not already
pip install pip-audit

# 2. Audit current requirements
pip-audit -r requirements.txt
# expected: "No known vulnerabilities found" or a list of CVEs with fix versions.

# 3. Inspect installed package names before installing
pip install --dry-run -r requirements.txt
# Read the resolver output. Reject any package whose name does not match what you expect.

# 4. Upgrade workflow (single dep at a time) — see "Upper-bound pins" above for the full procedure
pip-audit -r requirements.txt          # baseline
# edit requirements.txt to bump one version
pip install -r requirements.txt
make test                               # full suite — 300+ tests as of Day 71
git diff requirements.txt               # commit the diff

# 5. Cron a monthly audit on the VPS (or run before every deploy)
ssh root@204.168.204.221 'cd /root/kraken-bot && /root/kraken-bot/venv/bin/pip-audit -r requirements.txt'
```

---

## 6. Incident response

### Threat
- Realizing in the middle of a market move that something is wrong, and not knowing the first command to run.
- Forgetting which evidence to capture before changing state, making postmortem impossible.

### Posture
A four-phase response: **STOP → CAPTURE → INVESTIGATE → RECOVER**. Always in that order. Never investigate before stopping if money is moving against you.

### Concrete actions

#### Phase 1 — STOP (under 60 seconds)
```bash
# Halt trading immediately
ssh root@204.168.204.221 'sed -i "s/^DRY_RUN=.*/DRY_RUN=true/" /root/kraken-bot/.env && systemctl restart kraken-bot'

# If you suspect the VPS is compromised, full stop:
ssh root@204.168.204.221 'systemctl stop kraken-bot'

# If you suspect KEYS are compromised, disable them in the Kraken dashboard
# IMMEDIATELY at https://www.kraken.com/u/security/api before doing anything else.
```

#### Phase 2 — CAPTURE (under 5 minutes)
```bash
TS=$(date +%Y%m%d_%H%M%S)
mkdir -p ~/incident-$TS && cd ~/incident-$TS

# Snapshot everything we will need for forensics
ssh root@204.168.204.221 'journalctl -u kraken-bot --since "24 hours ago" --no-pager' > journal.log
ssh root@204.168.204.221 'cat /root/kraken-bot/bot.log'                                > bot.log
ssh root@204.168.204.221 'cat /root/kraken-bot/positions.json'                         > positions.json
ssh root@204.168.204.221 'cat /root/kraken-bot/trades.csv'                             > trades.csv
ssh root@204.168.204.221 'last -n 50'                                                  > logins.log
ssh root@204.168.204.221 'ps auxf'                                                     > processes.txt
ssh root@204.168.204.221 'ss -tnlp'                                                    > listening_ports.txt
ssh root@204.168.204.221 'journalctl -u ssh --since "24 hours ago" --no-pager'         > ssh.log

# Pull a Kraken account-level audit
# Web: https://www.kraken.com/u/history/trades and /u/history/ledgers — export CSVs.
```

#### Phase 3 — INVESTIGATE
- Compare `positions.json` to the Kraken ledger export. Any trades on Kraken that the bot did not record are evidence of a compromise (keys leaked) or a manual trade you forgot.
- Search `journal.log` for unexpected coins, oversized orders, or sells you did not authorize.
- Search `logins.log` and `ssh.log` for SSH sessions from unknown IPs.
- Search `processes.txt` for anything that is not `python main.py`, `sshd`, or the standard Ubuntu services.

#### Phase 4 — RECOVER
- If keys were compromised: rotate (see section 2), re-deploy, then re-enable trading.
- If code was compromised: roll back to a known-good commit (see [OPS_RUNBOOK.md](OPS_RUNBOOK.md) section 5).
- If positions diverged from `positions.json`: edit the file to match Kraken reality before re-enabling.
- Write a postmortem in `JOURNAL.md` covering: timeline, root cause, what worked in this response, what to add to the threat model. Treat the postmortem as required, not optional.
- Re-enable trading by setting `DRY_RUN=false` and `systemctl restart kraken-bot`. Watch one full cycle before stepping away.

---

## Hardening backlog

Everything originally listed here — the `KILL` switch, retry/rate-limiter, drawdown circuit breaker, JSONL trade log, status file, and trade notifications — has shipped (Days 18-28 range; see `DAILY_ITERATIONS.md` and `JOURNAL.md` for specifics). One item remains open:

- **Systemd unit committed to repo** (`deploy/kraken-bot.service`) — blocked on VPS SSH access, tracked as Day 56 in `DAILY_ITERATIONS.md`.

Once that lands, this file's threat model will be fully backed by shipped controls rather than planned ones.
