# Decision: subagent `ui-tester`

- **Problem / trigger**: Playwright MCP calls produce screenshots and page snapshots that swamp the main context; the tester should return pass/fail per spec scenario. Serves `002-flagpole-web` acceptance scenarios.
- **Alternative rejected**: driving Playwright MCP from the main session (context flood); headless `npx playwright test` only (`/e2e` covers that; this agent explores scenarios the suite does not yet encode).
- **Limits**: `tools: Read, Glob, mcp__playwright__*, mcp__flagpole-mcp__*` (browser + flag state only, no shell, no edits), `maxTurns: 40`.
- **Not done**: no `skills:` preload (the spec path is passed in the prompt). Signal: the same login procedure explained in every prompt → preload a `ui-login` skill.
- **Verification**: `/agents`; walkthrough in Phase 3 against the dev server with screenshot paths. Pending.
