.DEFAULT_GOAL := help

VENV   := venv/bin
SERVER := root@204.168.204.221
REMOTE_DIR := /root/kraken-bot

.PHONY: help test run dry deploy logs restart status

help:
	@echo "kraken-bot make targets:"
	@echo "  make test     run the pytest suite"
	@echo "  make run      run the bot (scheduler loop, live .env)"
	@echo "  make dry      run a single cycle with --once --dry-run"
	@echo "  make deploy   test, then rsync to the VPS (excludes .env) and restart the service"
	@echo "  make logs     tail the last 50 journalctl lines on the VPS"
	@echo "  make restart  restart the systemd service on the VPS"
	@echo "  make status   show systemd status on the VPS"

test:
	$(VENV)/python3 -m pytest -q

run:
	$(VENV)/python3 main.py

dry:
	$(VENV)/python3 main.py --once --dry-run

# Mirrors the manual deploy ritual in OPS_RUNBOOK.md section "Deploy procedure" —
# rsync (not scp) so .env and .git on the server are never clobbered.
deploy: test
	rsync -av --exclude='.env' --exclude='.git' --exclude='venv' --exclude='__pycache__' \
		./ $(SERVER):$(REMOTE_DIR)/
	ssh $(SERVER) 'systemctl restart kraken-bot'
	ssh $(SERVER) 'journalctl -u kraken-bot -n 20 --no-pager'

logs:
	ssh $(SERVER) 'journalctl -u kraken-bot -n 50 --no-pager'

restart:
	ssh $(SERVER) 'systemctl restart kraken-bot'

status:
	ssh $(SERVER) 'systemctl status kraken-bot --no-pager'
