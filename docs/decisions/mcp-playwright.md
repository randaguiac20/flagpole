# Decision: MCP server `playwright` (project scope, `.mcp.json`)

- **Problem / trigger**: Claude cannot drive a browser from Bash; verifying the UI after changes and the `ui-tester` agent need it. Serves `002-flagpole-web`.
- **Alternative rejected**: `npx playwright test` only (deterministic suite, but no exploratory verification); `claude-in-chrome` (needs the extension and a visible browser).
- **Limits**: official `@playwright/mcp` pinned to `0.0.80`, `--headless --isolated`, screenshots to `.claude/logs/playwright` (gitignored), stdio (no port). Same name exists in the user scope on this machine: project scope wins (documented precedence lesson).
- **Not done**: no `--save-session`/traces, no vision caps. Signal: a bug only reproducible with a persistent profile.
- **Verification**: `/mcp` shows `playwright` connected from project scope; `claude mcp list`. Pending: user approval dialog on first session (`claude mcp reset-project-choices` to replay it).
