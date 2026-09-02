# Decision: skill `/e2e`

- **Problem / trigger**: running Playwright headless with the right base URL, then mapping failures to spec scenario IDs and the HTML report path. Serves `002-flagpole-web`, `005` (in-cluster target).
- **Alternative rejected**: `make e2e` alone (no scenario mapping); `ui-tester` agent (exploratory, MCP-driven; `/e2e` is the deterministic suite).
- **Limits**: model-invocable, `allowed-tools` = `make e2e`, `scripts/e2e.sh`, `scripts/ports.sh`, Read; never edits tests.
- **Not done**: no automatic retries/flake quarantine (determinism is a constitution principle). Signal: a genuinely flaky test → fix the test, not the skill.
- **Verification**: invoked 2026-09-02 on 002-flagpole-web: `9 passed (9.4s)`, report at `frontend/playwright-report/index.html`. The first invocation exposed three drifts in this file (a `TARGET` variable the Makefile never had, a `SC-nnn` test-naming claim, and prose arguments landing in `$0`/`$1`); see gotcha #21.
