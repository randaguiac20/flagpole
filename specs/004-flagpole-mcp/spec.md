# Feature Specification: flagpole-mcp

**Feature Branch**: `004-flagpole-mcp`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "004-flagpole-mcp: a small stdio server that lets an assistant read and change Flagpole flag state directly, so a browser-driving agent can put the system into a Given state before it tests a scenario. Three tools (list_flags, get_flag, set_flag_state), one resource (the current flag state), one prompt (a rollout-check template). It talks to flagpole-api over HTTP and holds no state of its own. Authenticates as a service, like the consumer does. Non-goals: no evaluation, no audit writing beyond what the API already records, no second copy of any rule."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - An agent puts the system into a known state before testing (Priority: P1)

The `ui-tester` agent has a scenario that begins "Given `new_banner` is enabled at 100 percent in
dev". Today it cannot arrange that: its tool list is the browser and this server, and the browser
route means signing in as an operator and clicking through the web app, which is the very thing under
test. With this server it sets the state directly, then drives the browser to check the behaviour.

**Why this priority**: This is the only reason the server exists. Without it the agent's Given steps
are either impossible or performed through the interface it is supposed to be testing, which makes a
passing test meaningless.

**Independent Test**: From an assistant session, set `new_banner` to enabled at 100 in dev through
this server, then read the flag back and see the new state.

**Acceptance Scenarios**:

1. **Given** a running flag service, **When** the assistant lists flags, **Then** it receives every
   flag with both environments' state.
2. **Given** flag `new_banner`, **When** the assistant sets `dev` to enabled at 100, **Then** the
   change is visible to the web app and the consumer on their next load.
3. **Given** a flag key that does not exist, **When** the assistant sets its state, **Then** it
   receives a clear message naming the unknown key, and nothing is changed.
4. **Given** a rollout percentage outside 0–100, **When** the assistant sets it, **Then** the change
   is refused with a message naming the allowed range.

---

### User Story 2 - The assistant can read flag state without being told how (Priority: P2)

The assistant reads the current flag state as a resource, without composing a call or knowing the
service's address. A prompt template turns "is this rollout sensible?" into a consistent question with
the state already filled in.

**Why this priority**: It is what distinguishes a server from a wrapper around one shell command. The
resource and the prompt exist to demonstrate the two capabilities beyond tools, and the walkthrough
must show all three used at least once. The feature is useful with tools alone, so this is P2.

**Independent Test**: Read the flag-state resource in an assistant session and see current state
without calling a tool; then invoke the prompt and see the state embedded in it.

**Acceptance Scenarios**:

1. **Given** flags exist, **When** the assistant reads the flag-state resource, **Then** it receives
   the current state of every flag in both environments.
2. **Given** any flag, **When** the assistant invokes the rollout-check prompt for it, **Then** the
   prompt contains that flag's current state in both environments.

---

### User Story 3 - It fails in a way an assistant can act on (Priority: P3)

Every failure — the flag service unreachable, credentials refused, a bad argument — comes back as a
message that says what went wrong and what to do about it, never as a stack trace or a silent empty
result.

**Why this priority**: An assistant cannot see logs. A tool that fails vaguely produces a confident
wrong answer in the session that called it, which is worse than an error. P3 because the happy paths
in US1 and US2 are what make the server useful at all.

**Independent Test**: Stop the flag service and call each tool; each returns a message naming the
cause.

**Acceptance Scenarios**:

1. **Given** the flag service is unreachable, **When** any tool is called, **Then** the result says
   the flag service could not be reached and names the address that was tried.
2. **Given** the service refuses the server's credentials, **When** any tool is called, **Then** the
   result says so, distinctly from an outage.
3. **Given** any failure, **When** the result is returned, **Then** it contains no token, no key and
   no stack trace.

---

### Edge Cases

- **No flags at all**: listing returns an empty list and says so, rather than looking broken.
- **A flag key that does not match the service's rules**: refused with the rule stated, before any
  call is made.
- **Setting the state a flag already has**: succeeds. The flag service treats it as a write and
  audits it, and this server does not second-guess that.
- **A very large flag list**: returned in full. There is no paging, because the demo has a handful of
  flags and inventing paging here would be a second, divergent copy of the service's own rules.
- **The flag service is a different version than this server expects**: an answer that does not match
  the documented shape is an error naming the mismatch, not a partially-read result.

## Clarifications

### Session 2026-09-02

- Q: A service token grants viewer rights only, but this server must write. How does it get
  permission? → A: The flag service gains one named operator service issuer, configured explicitly
  and off by default (001 FR-020). Audit entries name `flagpole-mcp`, which is accurate — the
  assistant made the change. Holding a real operator's token was rejected: it would attribute the
  change to a person who did not make it, and would expire mid-run.
- Q: What happens when that grant is not configured? → A: The flag service has two service slots, one
  viewer and one operator, and a deployment decides which slot (if either) this server occupies. In
  the viewer slot it reads and is refused writes; in neither slot its credentials are refused
  outright. The role is a property of the slot, never of the token (FR-011a).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The server MUST expose a tool that lists every flag with both environments' state.
- **FR-002**: The server MUST expose a tool that returns one flag by key, including both
  environments' state.
- **FR-003**: The server MUST expose a tool that sets one flag's state in one environment (enabled
  and rollout percentage).
- **FR-004**: The server MUST expose the current flag state as a resource the assistant can read
  without calling a tool.
- **FR-005**: The server MUST expose a prompt template for reviewing a flag's rollout, with that
  flag's current state already filled in.
- **FR-006**: The server MUST hold no flag state of its own: every answer comes from the flag service
  on the call that produced it, and nothing is cached between calls.
- **FR-007**: The server MUST NOT evaluate flags, reimplement the rollout rule, or write audit
  entries itself. The flag service remains the only place those happen.
- **FR-008**: The server MUST validate arguments before calling the flag service — flag key shape and
  rollout range — and refuse with a message naming the rule.
- **FR-009**: Every failure MUST be returned as a message naming the cause, distinguishing an
  unreachable service, refused credentials, an unknown flag, and an invalid argument.
- **FR-010**: No result, message or log line may contain the server's credentials or key material.
- **FR-011**: The server MUST authenticate to the flag service as a service, using the same token
  arrangement as the consumer (a short-lived signed token naming its environment), with its own key
  pair rather than the consumer's.
- **FR-011a**: The server MUST hold operator rights only because the flag service was explicitly
  configured to grant them to its issuer (001 FR-020). When the flag service instead trusts it as an
  ordinary service, reads MUST work and a write MUST be refused with a message saying the server has
  not been granted operator rights. When the flag service does not trust its issuer at all, every
  call MUST report refused credentials, distinctly from an outage.
- **FR-012**: The server MUST run over standard input and output, with no listening port.
- **FR-013**: The flag service's address, the environment, and the credential paths MUST be
  configuration, with no code change needed to point it at another environment.
- **FR-014**: The server MUST refuse to start when its environment is not one the flag service
  recognises.

### Key Entities

- **Flag view**: what a tool or the resource returns for one flag — key, description, and both
  environments' enabled state and rollout percentage. A pass-through of the flag service's shape, not
  a second model.
- **Server configuration**: flag service address, environment, credential paths. Supplied at startup;
  never edited at run time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An assistant can set a flag's state and see that state reflected by the web app and the
  consumer on their next load, with no restart of anything.
- **SC-002**: The `ui-tester` agent can arrange a scenario's Given state without using the web app.
- **SC-003**: With the flag service stopped, every tool returns a message naming the cause, and none
  hangs or returns an empty success.
- **SC-004**: All three capability kinds — tool, resource and prompt — are exercised at least once in
  the project walkthrough with real output.
- **SC-005**: No output of any tool, resource or prompt ever contains the server's credentials.
- **SC-006**: Setting a flag through this server and setting it through the web app produce the same
  audit trail in the flag service, because both go through the same endpoint.

## Assumptions

- This server is a **learning artifact as much as a tool**. A short shell command with a token would
  do the same job for a human. It is built because the `ui-tester` agent needs flag state and cannot
  run shell commands, and because building one MCP server is a stated goal of the project. That
  honesty belongs in the decision record, not hidden.
- It authenticates with the same service-token arrangement feature 003 introduced, including the
  environment claim. It gets its own key pair rather than sharing the consumer's, so revoking one does
  not revoke the other.
- A service token grants viewer rights only (001 FR-019). Setting flag state needs more, so the flag
  service gains one explicitly-configured operator service issuer (001 FR-020), which this server
  uses and the consumer does not. It is off unless set, and the production overlay never sets it.
- The flag service, its seeded flag, and the shape of its answers come from feature 001. This feature
  adds no endpoint to it beyond what the open question settles.
- Transport is standard input and output. No HTTP transport, no port, no authentication of the
  assistant to this server: it runs as a child process of the session that started it.
