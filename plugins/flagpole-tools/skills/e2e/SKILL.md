---
name: e2e
description: Run the Playwright end-to-end suite headless against the local Flagpole dev stack and summarize the HTML report. Use after UI changes or before merging a feature branch.
argument-hint: "[-g <test-name-filter>]"
allowed-tools: Bash(make e2e *), Bash(scripts/ports.sh *), Read
---

Run the end-to-end suite. Everything it needs (Dex, the migrated and seeded API, the web dev server)
is started by `frontend/playwright.config.ts`, so nothing has to be running first.

Preflight (show the output):
!`scripts/ports.sh table 2>/dev/null | grep -E 'WEB|API|DEX' || true`

1. `make e2e ARGS="$ARGUMENTS"` — headless `npx playwright test`. The HTML report lands in
   `frontend/playwright-report/`; traces and screenshots are kept for failures only.
2. If a port the config needs is already taken, stop and say which one. Do not kill the process holding it.
3. Summarize: passed/failed/skipped counts and, for each failure, the test name (they carry their
   story and scenario, e.g. `US3-1`), the assertion, and the screenshot path.
4. Do not modify tests to make them pass. A failing scenario means either the code or the spec is
   wrong; say which you believe and why.

This suite runs against **localhost only**. `frontend/playwright.config.ts` hardcodes
`baseURL: http://localhost:${WEB_PORT}` and starts its own Dex, API and web server; `make e2e` takes
`ARGS` and nothing else. There is no cluster target — an earlier version of this file advertised
`make e2e TARGET=cluster`, which never existed (gotcha #50). Do not offer it.

So a green run here says the code is right, not that the cluster is. The two can disagree whenever
they obtain a component differently — feature 005 ran Dex 2.44.0 from a chart while
`docker-compose.dev.yaml` ran 2.45.1, and this suite passed throughout while every cluster user got
the wrong role. To check the deployed system, verify against it directly (`scripts/verify-cluster.sh`,
or the `ui-tester` agent, whose Playwright MCP server can reach the cluster hosts).
