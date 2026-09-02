# MCP servers

Source: https://code.claude.com/docs/en/mcp

## What / where

MCP connects Claude to tools, resources and prompts served by another process. Transports: `stdio` (Claude Code spawns the process; no port), `http` (`streamable-http`), `sse`, `ws`. Scopes and precedence for the same name: **local** (`~/.claude.json`, per project, private) > **project** (`.mcp.json`, committed) > **user** (`~/.claude.json`) > plugins > claude.ai connectors. Project servers need a one-time approval (`claude mcp reset-project-choices` to replay; `enableAllProjectMcpServers` to skip, which we do not set).

`.mcp.json` shape: `{"mcpServers": {"name": {"type": "stdio", "command": …, "args": […], "env": {…}}}}` with `${VAR}` / `${VAR:-default}` expansion; a missing variable without a default only warns. `CLAUDE_PROJECT_DIR` is set in the server's environment, so in `.mcp.json` write `${CLAUDE_PROJECT_DIR:-.}`. Per-server `timeout` (ms) overrides `MCP_TOOL_TIMEOUT`.

CLI: `claude mcp add --transport stdio <name> -- <cmd>` (`--scope project|user`), `claude mcp add-json`, `claude mcp list` (health), `claude mcp get`, `claude mcp remove`, `claude mcp login <name>` (OAuth). In session: `/mcp` (status, reconnect, OAuth), `/context all` for per-tool token cost. Tool names in permissions/hooks: `mcp__<server>__<tool>`; MCP prompts appear as `/mcp__server__prompt`; resources via `@server:resource`. Tool search is on by default: only names load until a tool is used.

## When / how far

Trigger: data or actions Claude cannot reach through the shell (a browser), or learning to build a server (say so). If a CLI exists (`kubectl`, `flux`, `gh`, `curl`), prefer Bash + a skill. This repo: 1 official (`playwright`) + 1 custom (`flagpole-mcp`, feature 004); `cluster-status-mcp` was cut (see `docs/decisions/cluster-status-mcp.md`). stdio by default; anything binding a port goes through `scripts/ports.sh`.

## Our implementation

- `playwright`: `npx @playwright/mcp@0.0.80 --headless --isolated --output-dir .claude/logs/playwright`. The same name exists in the user scope on the author's machine; the project entry wins, which is the precedence lesson.
- `flagpole-mcp` (feature 004): Python `mcp` SDK 2.1.1 (`from mcp.server import MCPServer`, not `FastMCP` — gotcha #8). Tools `list_flags`, `get_flag`, `set_flag_state`; resource `flagpole://flags`; prompt `rollout_check`. stdio, no port. Tested with the in-memory `Client` against the server object, so a capability that was never registered fails a test rather than a demo (61 tests). The names above are fixed by `specs/004-flagpole-mcp/contracts/mcp-surface.json`, which the suite asserts the published schema against.

  Three things worth copying:

  - **Argument rules go in the tool signature.** `key: FlagKey`, `env: Env`, `enabled: StrictBool`, `rollout_percent: Annotated[int, Field(ge=0, le=100)]` become the published input schema, so the assistant is told the rules in advance and the SDK refuses a breaking call before the body runs. `StrictBool` matters: ordinary coercion turns the string `"false"` into `True`, and the call would look like it worked.
  - **Every capability is total.** No exception escapes; each failure returns `{"error": {"kind", "message"}}` with six distinguishable kinds, because an assistant cannot read logs and the remedies differ.
  - **Logging goes to stderr, explicitly.** On stdio, stdout *is* the protocol; one stray `print` kills the session with a parse error. A test asserts a tool call writes nothing to stdout.

  Its rights come from configuration on the flag service (the operator slot, 001 FR-020), never from a claim in its token, and the production overlay never grants them.

## How to verify

`/mcp` → `playwright: connected (project)` and `flagpole-mcp: connected (project)`; `claude mcp list` from the repo root; a tool call appears as `mcp__playwright__browser_navigate` or `mcp__flagpole-mcp__set_flag_state`. `flagpole-mcp` can also be driven outside a session — `cd mcp/flagpole-mcp && uv run python -m flagpole_mcp </dev/null` must exit quietly, which is the one thing the in-memory tests cannot show. Pending: user session for the `/mcp` output.

## Common mistakes

Secrets in `.mcp.json` (use `${VAR}`); HTTP servers binding fixed ports for no reason; wrapping a CLI; the same server name in two scopes without knowing which wins; forgetting the project-approval dialog in headless runs (`-p` loads without prompting).
