.DEFAULT_GOAL := help

VENV   := venv/bin
SERVER := root@204.168.204.221
REMOTE_DIR := /root/kraken-bot

.PHONY: help test coverage lint run dry deploy logs restart status

help:
	@echo "kraken-bot make targets:"
	@echo "  make test      run the pytest suite"
	@echo "  make coverage  run the suite with a per-file coverage report (Day 72)"
	@echo "  make lint      run the non-pytest CI gates locally: pip-audit, bandit, shellcheck, yamllint (Day 119)"
	@echo "  make run       run the bot (scheduler loop, live .env)"
	@echo "  make dry       run a single cycle with --once --dry-run"
	@echo "  make deploy    test, rsync to the VPS (excludes .env), restart, verify heartbeat"
	@echo "  make logs      tail the last 50 journalctl lines on the VPS"
	@echo "  make restart   restart the systemd service on the VPS"
	@echo "  make status    show systemd status on the VPS"

test:
	$(VENV)/python3 -m pytest -q

# Day 72: bot source only — tests/, venv/, and site-packages excluded via
# .coveragerc so the report reflects what the *bot* exercises, not the
# near-100%-self-covering test files themselves.
#
# Day 83: CI runs this same scope with --cov-fail-under (see
# .github/workflows/test.yml for the current threshold, raised 95 -> 96 on
# Day 94, then 96 -> 97 on Day 112) on every push — raise it further when
# coverage improves and
# holds; never lower it to pass a PR.
coverage:
	$(VENV)/python3 -m pytest --cov=. --cov-report=term-missing -q

# Day 119: `make test`/`make coverage` only ever ran pytest, but CI (see
# .github/workflows/test.yml) has grown four more gates since (pip-audit on
# Day 58, bandit on Day 118, shellcheck on Day 115, yamllint on Day 116) with
# no local equivalent — a contributor running `make test` green locally could
# still push a CI-only failure in any of the four. mypy is already covered
# by the pytest suite itself (tests/test_*_types.py), so it's not repeated
# here. shellcheck/yamllint are system packages, not pip ones — install them
# separately (e.g. `apt-get install shellcheck yamllint`) if this fails with
# "command not found". bandit excludes ./venv as well as ./tests: CI's
# `bandit -r . -x ./tests` never sees a venv/ (GitHub Actions installs
# dependencies without one), but this Makefile's own convention puts one at
# the repo root, and without the exclude bandit scans every third-party
# package inside it too.
lint:
	$(VENV)/python3 -m pip_audit -r requirements.txt -r requirements-dev.txt
	$(VENV)/python3 -m bandit -r . -x ./tests,./venv
	shellcheck scripts/*.sh
	yamllint .github/workflows/test.yml .github/dependabot.yml

run:
	$(VENV)/python3 main.py

dry:
	$(VENV)/python3 main.py --once --dry-run

# Day 57: test + rsync + restart + heartbeat verification, all fail-loud.
# See scripts/deploy.sh for the step-by-step and OPS_RUNBOOK.md for the
# manual fallback ritual this replaces.
deploy:
	./scripts/deploy.sh

logs:
	ssh $(SERVER) 'journalctl -u kraken-bot -n 50 --no-pager'

restart:
	ssh $(SERVER) 'systemctl restart kraken-bot'

status:
	ssh $(SERVER) 'systemctl status kraken-bot --no-pager'
