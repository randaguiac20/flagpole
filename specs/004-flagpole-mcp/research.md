# Research: 004-flagpole-mcp

Phase 0. Each item is a decision that was open when the plan started, with what it rules out.

## D1 — Which SDK surface to build against

- **Decision**: `mcp` 2.1.1. The server class is `from mcp.server import MCPServer`; capabilities are
  declared with the `@tool`, `@resource` and `@prompt` decorators; the process is started with
  `await server.run_stdio_async()`. Tests use `from mcp import Client` against the server object.
- **Rationale**: Verified on this host on 2026-09-02 — `mcp.__version__` is 2.1.1, `mcp.server`
  exports `MCPServer`, and `Client` is a top-level export. The name `FastMCP` that most material
  still uses was renamed; writing against the older name would not import. This is gotcha #8.
- **Alternatives**: pinning an older `mcp` to keep the `FastMCP` name (installing a superseded SDK to
  match stale documentation); implementing the protocol by hand (a second, divergent implementation
  of a specification that already has one).

## D2 — How the server proves who it is

- **Decision**: The same arrangement 003 introduced: an RS256 token signed with the server's own
  private key, with `iss` `flagpole-mcp`, `sub` `flagpole-mcp`, the flag service's audience, the
  `env` claim, five-minute expiry and no `groups`. Its own key pair, not the consumer's.
- **Rationale**: The identity provider offers no unattended grant (verified in 003, C1), and reusing
  the arrangement means one authentication path rather than two. Separate keys mean revoking the
  assistant's access does not stop the consumer serving pages, and the audit trail can tell the two
  services apart because the issuer differs.
- **Alternatives**: sharing the consumer's key (one revocation takes down both; the audit trail
  cannot distinguish them); a static shared secret (a weaker second path, rotated by editing two
  services).

## D3 — How it gets permission to write

- **Decision**: `flagpole-api` gains `FLAGPOLE_OPERATOR_SERVICE_ISSUER`, naming at most one service
  issuer whose tokens resolve to the operator role. Unset by default; refused if it names an issuer
  the service does not otherwise trust. Everything else about service tokens is unchanged — they
  still carry no groups, and groups on a service token are still ignored.
- **Rationale**: The grant is a property of the deployment, not of the token, so it cannot be
  forged: a token cannot claim it. It is one named issuer rather than a list, because the demo needs
  one and a list would invite a production deployment to accumulate them. Audit entries name
  `flagpole-mcp`, which is the truth — the assistant made the change.
- **Alternatives**: honouring a `groups` claim on service tokens (the token would carry its own
  authority, which is exactly what the no-bypass rule prevents); a `role` claim (same objection); a
  separate write endpoint for services (a second authorization path).

## D4 — Where the operator grant must never be set

- **Decision**: local development and the `dev` overlay only. The production overlay does not set it,
  and feature 005 adds a check that the manifests do not.
- **Rationale**: Nothing in the service can tell a real production from a demo, so the boundary has
  to be the deployment. Saying so plainly and testing the manifests is honest; pretending the service
  enforces it would not be.
- **Alternatives**: refusing the setting when the environment is `prod` (a service deciding what its
  own environment means, which would be circumvented by naming the environment something else); no
  boundary at all (an assistant with write access to production flags).

## D5 — What a failure looks like

- **Decision**: Every failure returns a message naming the cause and the address that was tried, with
  four distinguishable kinds: unreachable, credentials refused, unknown flag, invalid argument. No
  exception escapes a tool; no message contains a token, a key or a traceback.
- **Rationale**: An assistant cannot read logs, so the message is the only channel. A tool that fails
  vaguely produces a confident wrong answer in the session that called it. Distinguishing the four
  kinds matters because the remedies differ: start the service, configure the grant, check the key,
  fix the argument.
- **Alternatives**: letting exceptions propagate as protocol errors (the assistant sees a traceback
  and no remedy); one generic failure message (the four remedies collapse into guesswork).

## D6 — Logging must not touch standard output

- **Decision**: Logging is configured to stderr explicitly, and a test asserts that a tool call
  writes nothing to stdout beyond the protocol.
- **Rationale**: On stdio transport, stdout *is* the protocol. One stray `print` corrupts the stream
  and the session's connection dies with an unhelpful parse error. This is the classic stdio-server
  mistake and it is cheap to test for.
- **Alternatives**: relying on the discipline of not printing (the failure is silent until it is not).

## D7 — No shared package for the token signer

- **Decision**: `mcp/flagpole-mcp/flagpole_mcp/tokens.py` is its own ~40-line module. What the two
  services share is `specs/003-flagpole-consumer/contracts/service-token.json`, which both test
  suites assert against.
- **Rationale**: A shared package would add a build artifact, a version and an install step to two
  services to save forty lines. The risk duplication actually carries is drift, and a machine-readable
  contract that both suites check removes exactly that risk. If a third service needs it, the signal
  to extract a package will be real rather than anticipated.
- **Alternatives**: a `flagpole-common` distribution (machinery out of proportion); importing across
  service directories (couples their dependency sets and breaks the containers).

## D8 — Testing without a subprocess

- **Decision**: The SDK's in-memory `Client` is connected to the server object; the flag service is an
  httpx `MockTransport`. No process is spawned and no port is opened.
- **Rationale**: It exercises the real registration — a tool missing from the surface fails the test —
  without the flakiness of a subprocess and a pipe. The one thing it cannot prove is that the process
  starts, which `quickstart.md` covers by starting it for real once.
- **Alternatives**: spawning the server and speaking the protocol over pipes (slow, racy, and it hides
  the failure inside a timeout); testing the functions directly (would pass even if nothing were
  registered, which is the mistake this feature is most likely to make).

## D9 — What this server does *not* get

Recorded so the next reader does not wonder: no cache, no paging, no evaluation, no flag deletion, no
audit reading, no HTTP transport, no authentication of the assistant to the server (it is a child
process of the session). The honest note from the spec belongs here too: **a shell command with a
token would do this job for a human**. It exists because the `ui-tester` agent cannot run shell
commands, and because building one MCP server is a stated goal of the project.
