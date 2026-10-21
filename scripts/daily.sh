#!/usr/bin/env bash
# Picks today's task from DAILY_ITERATIONS.md: with no argument, the
# lowest-numbered "## Day N" entry that has no "**Result (...)**" paragraph
# yet (scripts/next_day.py, Day 123); pass a day number to print that day's
# block explicitly regardless of whether it's done.
# Usage: ./scripts/daily.sh [day_override]

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BACKLOG="$ROOT/DAILY_ITERATIONS.md"

if [[ ! -f "$BACKLOG" ]]; then
  echo "error: $BACKLOG not found" >&2
  exit 1
fi

if [[ $# -ge 1 ]]; then
  DAY="$1"
else
  DAY=$(python3 "$ROOT/scripts/next_day.py" "$BACKLOG")
fi

echo "Day $DAY of kraken-bot iteration."
echo

# Extract the block between "## Day N:" and the next "## Day " or "## " or EOF.
BLOCK=$(awk -v day="$DAY" '
  BEGIN { printing=0 }
  $0 ~ "^## Day " day ":" { printing=1; print; next }
  printing && /^## / { exit }
  printing { print }
' "$BACKLOG")

if [[ -z "$BLOCK" ]]; then
  echo "No '## Day $DAY:' entry found in $BACKLOG."
  echo "It may not be written yet -- open the file and add it, following the"
  echo "shape of the entries around it."
  exit 1
fi

echo "$BLOCK"
