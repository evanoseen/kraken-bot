#!/usr/bin/env bash
# Picks today's task from DAILY_ITERATIONS.md by day index since 2026-05-19.
# Usage: ./scripts/daily.sh [day_override]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKLOG="$ROOT/DAILY_ITERATIONS.md"
START="2026-05-19"

if [[ ! -f "$BACKLOG" ]]; then
  echo "error: $BACKLOG not found" >&2
  exit 1
fi

if [[ $# -ge 1 ]]; then
  DAY="$1"
else
  DAY=$(python3 -c "from datetime import date; print((date.today() - date(2026,5,19)).days + 1)")
fi

if (( DAY < 1 )); then
  echo "Today is before Day 1. Start date is $START."
  exit 0
fi

echo "Day $DAY of kraken-bot iteration."
echo

# Extract the block between "## Day N:" and the next "## Day " or "## " or EOF.
awk -v day="$DAY" '
  BEGIN { printing=0 }
  $0 ~ "^## Day " day ":" { printing=1; print; next }
  printing && /^## / { exit }
  printing { print }
' "$BACKLOG"

if (( DAY > 31 )); then
  echo
  echo "Past Day 31. Day 28 includes a directive to extend this backlog."
  echo "Open $BACKLOG and add Days 32+ following the same shape."
fi
