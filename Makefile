.DEFAULT_GOAL := help

VENV   := venv/bin
SERVER := root@204.168.204.221
REMOTE_DIR := /root/kraken-bot

.PHONY: help test coverage run dry deploy logs restart status

help:
	@echo "kraken-bot make targets:"
	@echo "  make test      run the pytest suite"
	@echo "  make coverage  run the suite with a per-file coverage report (Day 72)"
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
coverage:
	$(VENV)/python3 -m pytest --cov=. --cov-report=term-missing -q

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
