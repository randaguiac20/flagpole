# Quickstart: 004-flagpole-mcp

What to run to see the feature work, and what each step proves. Every command is run from the
repository root unless stated.

## Prerequisites

- `make bootstrap` has run once (uv is available, Python 3.12 pinned).
- The flag service is running on 18000 — `make dev` starts it along with Dex, the consumer and the
  web app.

## 1. Generate the key pair and grant operator rights

```bash
scripts/mcp-keys.sh                     # idempotent; writes mcp/flagpole-mcp/.keys/, gitignored
```

`make dev` exports the flag service's side:

```
FLAGPOLE_OPERATOR_SERVICE_ISSUER=flagpole-mcp
FLAGPOLE_SERVICE_PUBLIC_KEY_PATH=...    # unchanged: the consumer's viewer issuer
```

**Proves**: the grant is configuration on the flag service, not a claim in the token (001 FR-020).
Unset it and the same server can still read but no longer write.

## 2. Run the unit tests

```bash
cd mcp/flagpole-mcp && uv run pytest -q
```

**Proves**: the three tools, the resource and the prompt are registered under the names in
`contracts/mcp-surface.json`; every failure kind returns its message; no output contains a
credential; a tool call writes nothing to stdout.

## 3. Start it the way Claude Code does

```bash
cd mcp/flagpole-mcp && uv run python -m flagpole_mcp </dev/null
```

It should exit quietly on end-of-input rather than raise. This is the one thing the in-memory tests
cannot show: that the process starts at all (research D8).

**Proves**: the entry point works outside pytest.

## 4. Use it from a session

`.mcp.json` already lists the server. In a Claude Code session:

- `/mcp` lists `flagpole-mcp` as connected with its three tools, one resource and one prompt.
- Ask for the flag state — the assistant reads the resource, without calling a tool.
- Ask to enable `new_banner` at 100 in dev — the assistant calls `set_flag_state`.
- Load <http://localhost:18020/> — the consumer shows the banner, with reason `rollout_hit`.
- `GET /audit` on the flag service shows the change with `who = flagpole-mcp`.

**Proves**: US1 and US2 end to end, and SC-006 — a change made here is audited exactly like one made
in the web app, because both go through the same endpoint.

## 5. Watch it fail well

```bash
# with the flag service stopped
cd mcp/flagpole-mcp && uv run pytest -q -k failures
```

Then, in a session with the flag service actually stopped, call any tool: the result names the
address it tried. Unset `FLAGPOLE_OPERATOR_SERVICE_ISSUER`, restart the flag service, and call
`set_flag_state`: the result says this server has not been granted operator rights, which is a
different message from an outage.

**Proves**: US3 and SC-003.
