---
name: e2e
description: Run the Playwright end-to-end suite headless against a running Flagpole (local dev or the k3d cluster) and summarize the HTML report. Use after UI changes or before merging a feature branch.
argument-hint: "[local|cluster] [-g <test-name-filter>]"
allowed-tools: Bash(make e2e *), Bash(scripts/e2e.sh *), Bash(scripts/ports.sh *), Read
---

Run the E2E suite against `$0` (default `local` = `http://localhost:18010`; `cluster` = `https://dev.flagpole.localhost`).

Preflight (show the output):
!`scripts/ports.sh table 2>/dev/null | grep -E 'WEB|API' || true`

1. `make e2e TARGET=$0 ARGS="$1"` — runs `npx playwright test` headless with the report written to `frontend/playwright-report/` and traces on first retry.
2. If the target is not reachable, stop and tell the user which service to start (`make dev` or `/deploy-local`); do not try to start it from here.
3. Summarize: passed/failed/skipped counts, each failed test with its spec scenario ID (tests are named `SC-nnn ...`), and the path to `frontend/playwright-report/index.html`. Attach the first screenshot path of every failure.
4. Do not modify tests to make them pass. A failing scenario means either the code or the spec is wrong; say which you believe and why.
