# Implementation Plan: flagpole-mcp

**Branch**: `004-flagpole-mcp` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-flagpole-mcp/spec.md`

## Summary

A stdio MCP server that gives an assistant three tools, one resource and one prompt over the flag
service, so the `ui-tester` agent can arrange a scenario's starting state without driving the web app
it is supposed to be testing. It holds no state: every answer comes from `flagpole-api` on the call
that produced it.

It authenticates with the service-token arrangement 003 introduced — its own key pair, its own issuer
name, the `env` claim — and `flagpole-api` gains one more setting, `operator_service_issuer`, naming
the single service issuer whose tokens carry operator rights (001 FR-020). It is unset by default and
never set in the production overlay, so the default posture of the flag service is unchanged.

## Technical Context

**Language/Version**: Python 3.12, managed by uv (same toolchain as `backend/` and `consumer/`)

**Primary Dependencies**: `mcp` 2.1.1 (`MCPServer`, `@tool`/`@resource`/`@prompt`,
`run_stdio_async`); httpx for the calls to the flag service; PyJWT[crypto] to sign the service token;
pydantic-settings for configuration

**Storage**: None, and this is a requirement (FR-006), not an omission

**Testing**: pytest with the SDK's in-memory `Client` against the server object, and httpx
`MockTransport` for the flag service — no subprocess, no network, no sleeping

**Target Platform**: a child process of a Claude Code session, launched from `.mcp.json`

**Project Type**: MCP server over standard input and output, plus one setting added to `backend/`

**Performance Goals**: One tool call costs at most two upstream calls (mint is local). No caching, so
no staleness

**Constraints**: stdout belongs to the protocol — every log line goes to stderr, or the session
breaks. No credential in any result, message or log. No evaluation, no second copy of any rule

**Scale/Scope**: three tools, one resource, one prompt, roughly 250 lines plus tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Verdict |
|---|---|---|
| I. Spec is the source of truth | Behaviour traces to FRs; a change to 001 is specified before it is written | **PASS** — 001 FR-020 and the amendment were committed before this plan |
| II. Simplicity and restraint | Fewest moving parts that satisfy the spec | **PASS** — no cache, no shared library extracted for a 40-line signer (the machine-readable token contract is what both services share), no HTTP transport, no paging |
| III. Test-first and deterministic | Every behaviour has a test that fails first; no randomness, no sleeps | **PASS** — the SDK's in-memory `Client` exercises the real server object, and the flag service is a stub transport |
| IV. Security baseline | Every request authenticated; least privilege; no secret in output | **PASS** — operator rights are opt-in per issuer and refused when unconfigured; SC-005 asserts no credential reaches any output; the private key is read once and never logged |
| V. GitOps and reproducibility | Configuration, not code, per environment | **PASS** — address, environment and key paths are settings; the operator grant is a setting on the flag service that the production overlay does not set |

**Re-check after Phase 1 design**: unchanged. The one judgement call worth naming is that the server
does **not** verify its own rights at startup by making a write. It reports what the flag service
answers when a write is actually attempted (FR-011a), because a startup probe would need a real flag
to write to, and would audit a change nobody asked for.

## Project Structure

### Documentation (this feature)

```text
specs/004-flagpole-mcp/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── mcp-surface.json # the three tools, the resource and the prompt, machine-readable
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
mcp/flagpole-mcp/
├── pyproject.toml
├── flagpole_mcp/
│   ├── __init__.py
│   ├── __main__.py      # entry point: build the server, run_stdio_async
│   ├── config.py        # Settings; refuses an unknown environment
│   ├── tokens.py        # signs the short-lived service token (RS256), per the 003 contract
│   ├── client.py        # the calls to flagpole-api; every failure becomes a named message
│   └── server.py        # @tool x3, @resource x1, @prompt x1
└── tests/
    ├── conftest.py      # server under an in-memory Client, stub flag service, throwaway key
    ├── test_tools.py    # US1
    ├── test_resource_and_prompt.py  # US2
    ├── test_failures.py # US3, and no credential in any output
    └── test_contract.py # the surface matches contracts/mcp-surface.json

backend/                 # amended by this feature
├── app/
│   ├── config.py        # operator_service_issuer (001 FR-020)
│   └── auth.py          # a service token from that issuer resolves to operator
└── tests/
    └── test_service_token.py  # the grant is off by default, on when named, never for the other issuer

scripts/
└── mcp-keys.sh          # generates mcp/flagpole-mcp/.keys/{service.key,service.pub}
```

## Complexity Tracking

| Addition | Why it is not avoidable | What was rejected |
|---|---|---|
| An operator grant for one service issuer | The server's whole purpose is arranging state, which is a write; a service token is a viewer by construction | Sharing an operator's real token (records a person as the author of a change they did not make, and expires mid-run); an unauthenticated write path for localhost (a second authentication path, which 001 FR-011 exists to prevent) |
| A second key pair | Revoking the assistant's access must not stop the consumer serving pages | Sharing the consumer's key (one revocation takes down two things, and the audit trail could no longer tell them apart) |
| A 40-line signer that resembles the consumer's | Extracting a shared package for it would add a build artifact, a version and an install step to two services to save forty lines | A `flagpole-common` package (more machinery than the duplication costs); importing across service directories (couples their dependency sets) |
