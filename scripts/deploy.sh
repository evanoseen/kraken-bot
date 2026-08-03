#!/usr/bin/env bash
# Day 57: one-command deploy.
#
# Runs the test suite, rsyncs the repo to the VPS (never clobbering .env),
# restarts the systemd service, then polls the Day 21 heartbeat file
# (last_run.txt) until it advances past its pre-deploy value. Fails loudly
# and non-zero at whichever step breaks, instead of the old multi-command
# ritual in OPS_RUNBOOK.md where a skipped step is easy to miss.
#
# Usage: ./scripts/deploy.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SERVER="root@204.168.204.221"
REMOTE_DIR="/root/kraken-bot"
HEARTBEAT_TIMEOUT=180   # seconds to wait for last_run.txt to advance
POLL_INTERVAL=5

cd "$ROOT"

echo "==> Running test suite..."
venv/bin/python3 -m pytest -q

echo "==> Capturing pre-deploy heartbeat..."
PRE_HEARTBEAT="$(ssh "$SERVER" "cat $REMOTE_DIR/last_run.txt 2>/dev/null || echo none")"
echo "    pre-deploy heartbeat: $PRE_HEARTBEAT"

echo "==> Syncing repo to $SERVER (excluding .env, .git, venv, __pycache__)..."
rsync -av --exclude='.env' --exclude='.git' --exclude='venv' --exclude='__pycache__' \
  ./ "$SERVER:$REMOTE_DIR/"

echo "==> Restarting kraken-bot.service..."
ssh "$SERVER" "systemctl restart kraken-bot"

echo "==> Waiting up to ${HEARTBEAT_TIMEOUT}s for the heartbeat to advance..."
elapsed=0
while (( elapsed < HEARTBEAT_TIMEOUT )); do
  sleep "$POLL_INTERVAL"
  elapsed=$((elapsed + POLL_INTERVAL))
  current_heartbeat="$(ssh "$SERVER" "cat $REMOTE_DIR/last_run.txt 2>/dev/null || echo none")"
  if [[ "$current_heartbeat" != "$PRE_HEARTBEAT" && "$current_heartbeat" != "none" ]]; then
    echo "==> Heartbeat advanced: $PRE_HEARTBEAT -> $current_heartbeat"
    echo "==> Deploy verified healthy."
    ssh "$SERVER" "journalctl -u kraken-bot -n 20 --no-pager"
    exit 0
  fi
  echo "    still waiting (${elapsed}s elapsed)..."
done

echo "!! Heartbeat did not advance within ${HEARTBEAT_TIMEOUT}s — deploy may have broken the bot." >&2
ssh "$SERVER" "journalctl -u kraken-bot -n 40 --no-pager" >&2 || true
exit 1
