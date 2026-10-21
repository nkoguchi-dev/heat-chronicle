.DEFAULT_GOAL := help
.NOTPARALLEL:
.PHONY: help setup dev stop check browser-smoke

help:
	@echo 'setup: install locked dependencies; dev: start local stack; stop: stop DB; check: quality checks; browser-smoke: production smoke'

setup:
	cd backend && uv sync --locked
	cd backend && uv run --locked --no-sync python ../tools/development.py setup

dev:
	cd backend && uv run --locked --no-sync python ../tools/development.py dev

stop:
	docker compose stop dynamodb-local

check:
	cd backend && uv run --locked --no-sync python ../tools/development.py check

browser-smoke:
	sh tools/run-browser-smoke.sh
