# Flagpole — entry points for humans, CI and Claude Code skills. Every target is idempotent.
SHELL := /usr/bin/env bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
-include .env
export

CLUSTER ?= $(or $(FLAGPOLE_CLUSTER_NAME),flagpole)

.PHONY: help bootstrap dev test test-fast test-hooks scan build cluster-up deploy e2e clean

# -h matters: `-include .env` puts a second file in MAKEFILE_LIST as soon as .env exists, and grep
# then prefixes every line with its filename, so awk printed "Makefile" as the target name for every
# row. Invisible until the first `make bootstrap` created .env.
help: ## list targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n",$$1,$$2}'

bootstrap: ## check tools, install deps, create the age key OUTSIDE the repo, install pre-commit
	@scripts/bootstrap.sh

dev: ## run api/web/consumer/dex locally on the ports from .env(.example)
	@scripts/dev.sh

test: test-hooks ## all unit tests + contract drift check (backend, consumer, mcp, frontend)
	@for d in backend consumer mcp/flagpole-mcp; do [ -f $$d/pyproject.toml ] && (cd $$d && uv run pytest -q) || true; done
	@[ -f frontend/package.json ] && (cd frontend && npm run api:types:check && npm test) || true
	@out=$$(scripts/check-tutorial.sh) || { echo "$$out"; exit 1; }; echo "$$out" | tail -1

test-fast: test-hooks ## the subset the Stop hook runs (< 60 s): hook tests + python unit tests
	@for d in backend consumer mcp/flagpole-mcp; do [ -f $$d/pyproject.toml ] && (cd $$d && uv run pytest -q -x -p no:cacheprovider) || true; done

test-hooks: ## shell tests for every hook, fed with sample stdin JSON
	@bash .claude/hooks/tests/run.sh

scan: ## all scanners (pip-audit, npm audit, osv-scanner, trivy, hadolint, gitleaks, bandit, semgrep)
	@scripts/scan.sh

build: ## docker images for api, consumer, web
	@scripts/build.sh

cluster-up: ## k3d cluster (Traefik disabled) + flux bootstrap github (asks before touching GitHub)
	@scripts/cluster-up.sh

deploy: ## import images into k3d, reconcile Flux, wait for Ready
	@scripts/deploy.sh

e2e: ## Playwright headless (starts API, Dex and the web dev server itself)
	@cd frontend && npx playwright test $(ARGS)

clean: ## remove local build/test artifacts (never the cluster, never keys)
	@rm -rf .claude/logs/* .claude/state/* frontend/test-results frontend/playwright-report
	@find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true
