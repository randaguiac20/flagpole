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

Cluster runs: `make e2e TARGET=cluster` points the suite at `https://dev.flagpole.localhost`. That
needs the cluster's self-signed CA trusted first (`docs/walkthrough.md` prints the command; it takes
sudo, so this skill will not run it).
