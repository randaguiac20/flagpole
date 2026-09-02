# Decision: skill `api-conventions` (reference, `user-invocable: false`)

- **Problem / trigger**: error shape, role mapping, `reason` values and cursor pagination must be identical across backend, consumer, MCP server and frontend client; needed sometimes, not every session. Serves `001`, `003`, `004`.
- **Alternative rejected**: CLAUDE.md (40 lines of reference in an always-on file); duplicating it in each spec (drift).
- **Limits**: knowledge only, no steps; hidden from the `/` menu; Claude loads it when designing/reviewing an endpoint.
- **Not done**: not preloaded into agents via `skills:`. Signal: `code-reviewer` misses a convention twice → preload.
- **Verification**: `/context` shows it in the skill list with its description; Phase 3 walkthrough shows Claude loading it. Pending.
