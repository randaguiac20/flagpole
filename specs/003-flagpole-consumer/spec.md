# Feature Specification: flagpole-consumer

**Feature Branch**: `003-flagpole-consumer`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "003-flagpole-consumer: the Flagpole consumer, a tiny service that shows what a feature flag actually does for a real user. One page and one endpoint, nothing else. GET / renders an HTML page for a user identified by a `user` query parameter (default `demo@flagpole.local`): it asks the flag service to evaluate the seeded flag `new_banner` for that user in the consumer's own environment, and renders the banner when the answer is enabled and a plain page when it is not. The page always shows the decision it acted on: the flag key, the environment, the user, enabled true/false, and the reason the service gave (env_disabled, rollout_hit, rollout_miss, unknown_flag). GET /healthz and /readyz are unauthenticated. The consumer authenticates to the flag service with its own client credentials, not a user token; the environment (dev or prod) and the flag service URL are configuration. Fail safe: if the flag service is unreachable, times out, or answers with an error, the consumer renders the plain page, reports reason `service_unavailable`, logs the failure, and still returns HTTP 200 — a broken flag service must never take the product down. Evaluation itself is never recomputed locally; the flag service is the only place that decides. Non-goals: no caching layer, no write operations, no user management, no styling framework, no database of its own. Use the GIT_BRANCH_NAME 003-flagpole-consumer."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The flag changes what a visitor sees (Priority: P1)

A visitor opens the consumer page. The consumer asks the flag service whether `new_banner` is on for
that visitor in the environment the consumer runs in, and renders accordingly: the banner appears when
the answer is enabled, and the page renders without it when the answer is not. An operator who changes
the flag in the flag service sees the visitor's page follow on the next load.

**Why this priority**: This is the whole point of a feature-flag service. Until a flag visibly changes
what somebody sees, the flags, environments and rollout percentages in features 001 and 002 are
bookkeeping. This story is the demonstration the rest of the product exists for.

**Independent Test**: Set `new_banner` to enabled at 100% in the consumer's environment, load the page,
see the banner; set it to disabled, reload, see the page without it. No other feature is needed beyond
a running flag service.

**Acceptance Scenarios**:

1. **Given** `new_banner` is enabled at 100 percent in the consumer's environment, **When** a visitor
   loads the page, **Then** the banner is shown.
2. **Given** `new_banner` is disabled in the consumer's environment, **When** a visitor loads the page,
   **Then** the page is rendered without the banner.
3. **Given** `new_banner` is enabled at 0 percent, **When** a visitor loads the page, **Then** the
   banner is not shown.
4. **Given** the flag state has just been changed by an operator, **When** the visitor reloads,
   **Then** the page reflects the new state on that load, with no restart and no waiting period.

---

### User Story 2 - The page survives a broken flag service (Priority: P2)

The flag service is down, slow, or refusing the consumer's credentials. The visitor still gets a
working page: the banner is simply absent, and the failure is recorded for whoever operates the
service rather than shown as an error.

**Why this priority**: A flag service that can take the product down with it is worse than no flag
service. This is the property that makes the whole arrangement safe to adopt, and it is the reason
the consumer exists as a separate service rather than a page inside the flag service.

**Independent Test**: Point the consumer at an address where nothing is listening, load the page, and
confirm it answers successfully without the banner and records why.

**Acceptance Scenarios**:

1. **Given** the flag service is unreachable, **When** a visitor loads the page, **Then** the request
   succeeds, the banner is absent, and the reported reason is `service_unavailable`.
2. **Given** the flag service is slower than the configured wait, **When** a visitor loads the page,
   **Then** the consumer stops waiting, renders the page without the banner, and reports
   `service_unavailable`.
3. **Given** the flag service refuses the consumer's credentials, **When** a visitor loads the page,
   **Then** the outcome is the same as any other failure: a page without the banner, reason
   `service_unavailable`, and a log entry that names the cause.
4. **Given** any of the failures above, **When** the operator inspects the service log, **Then** the
   failure appears there with enough detail to tell the three cases apart.

---

### User Story 3 - Anybody can see which decision was applied (Priority: P3)

The page states, in plain sight, the decision it acted on: which flag, which environment, which user,
whether it came out enabled, and the reason the flag service gave.

**Why this priority**: It turns the page from a demo into an explanation. Without it, a visitor who
does not see the banner cannot tell a disabled flag from a rollout miss from an outage — and neither
can the person giving the demo. It is P3 because the product behaviour in US1 and US2 is correct
without it.

**Independent Test**: Load the page for two different users while the flag is at a partial rollout and
confirm the panel reports different reasons for them.

**Acceptance Scenarios**:

1. **Given** any page load, **When** the visitor reads the page, **Then** it shows the flag key, the
   environment, the user, the enabled outcome, and the reason.
2. **Given** two users on opposite sides of a partial rollout, **When** each loads the page, **Then**
   one reports `rollout_hit` and the other `rollout_miss`, and the banner matches.
3. **Given** a flag key the service does not know, **When** the page loads, **Then** the reason shown
   is `unknown_flag` and the page renders without the banner.

---

### Edge Cases

- **No user given**: the page uses the default user, and the panel names the user it actually used, so
  nobody has to guess.
- **Empty or whitespace-only user**: treated as no user given.
- **Absurdly long or oddly encoded user**: the value is used as an opaque identifier and is escaped
  before it reaches the page; it never changes the page's structure.
- **Flag service answers something unexpected** (wrong shape, unparseable body): treated exactly like
  an outage — page without banner, reason `service_unavailable`.
- **Flag service answers slowly but within the wait**: the page is rendered normally; the wait is a
  ceiling, not a delay.
- **Environment misconfigured** (a value that is neither `dev` nor `prod`): the service refuses to
  start, rather than silently evaluating against an environment that does not exist.
- **Readiness during a flag-service outage**: the consumer stays ready. Its own health does not depend
  on the flag service, or an outage would remove the consumer from service and defeat US2.

## Clarifications

### Session 2026-09-02

- Q: The identity provider offers no client-credentials grant, so how does the consumer prove who it
  is to the flag service? → A: The consumer signs its own short-lived token with a private key, and the
  flag service validates it against a configured public key as a second trusted issuer alongside the
  identity provider. Service tokens carry no groups, so they hold viewer rights only.

This resolves FR-010 and adds FR-010a–c. It requires an amendment to feature 001, whose specification
described exactly one trusted issuer: see `specs/001-flagpole-api/spec.md` FR-011 and FR-019.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The consumer MUST serve one page at `/` that renders for a visitor identified by an
  optional `user` query parameter, defaulting to `demo@flagpole.local` when absent or blank.
- **FR-002**: For every page load, the consumer MUST ask the flag service to evaluate the flag
  `new_banner` for that user in the consumer's configured environment.
- **FR-003**: The consumer MUST NOT compute the evaluation itself, cache a previous answer, or infer
  an answer from flag state it has seen before. The flag service is the only place that decides.
- **FR-004**: The consumer MUST render the banner when, and only when, the flag service answers
  enabled.
- **FR-005**: The page MUST display the decision it acted on: flag key, environment, user, enabled
  outcome, and the reason returned by the flag service.
- **FR-006**: The consumer MUST surface every reason the flag service can give — `env_disabled`,
  `rollout_hit`, `rollout_miss`, `unknown_flag` — unchanged, plus `service_unavailable` for its own
  failures.
- **FR-007**: When the flag service is unreachable, answers an error, exceeds the configured wait, or
  returns something the consumer cannot read, the consumer MUST render the page without the banner,
  report the reason `service_unavailable`, and still answer the visitor successfully.
- **FR-008**: The consumer MUST record every such failure in its log with the cause, and MUST NOT show
  a stack trace, an internal address, or its credentials to the visitor.
- **FR-009**: The consumer MUST stop waiting for the flag service after a configured interval, so a
  hung flag service cannot hold a visitor's request open.
- **FR-010**: The consumer MUST authenticate to the flag service as itself, presenting a short-lived
  token it issues and signs with its own private key, and MUST NOT accept, forward, or require a
  visitor's credentials.
- **FR-010a**: The consumer's signing key MUST stay private to the consumer; only the matching public
  key is given to the flag service, and neither key is ever part of a page or a log line.
- **FR-010b**: Each token the consumer issues MUST be short-lived and MUST identify the consumer as its
  subject, so the flag service's audit trail names the service rather than a person.
- **FR-010c**: A service token MUST carry no group membership, and therefore MUST grant no more than a
  viewer can do. The consumer needs to evaluate flags and nothing else; a compromised consumer must not
  be able to change one.
- **FR-011**: The environment the consumer evaluates against, and the address of the flag service, MUST
  be configuration, with no code change required to run the same build in another environment.
- **FR-012**: The consumer MUST refuse to start when its environment is not one the flag service
  recognises, rather than starting and failing every evaluation.
- **FR-013**: The consumer MUST expose unauthenticated liveness and readiness endpoints, and its
  readiness MUST NOT depend on the flag service being reachable.
- **FR-014**: Any value that reaches the page from the request or from the flag service MUST be escaped
  so it renders as text.
- **FR-015**: The consumer MUST expose no write operation of any kind: it never creates, updates or
  deletes a flag, an environment state, or an audit entry.

### Key Entities

- **Decision**: what the consumer acted on for one page load — flag key, environment, user, enabled
  outcome, reason, and whether it came from the flag service or from the fail-safe path. Held only for
  the duration of the request; nothing is stored.
- **Consumer configuration**: the environment this instance represents, the flag service address, the
  wait ceiling, and the service's own credentials. Supplied at deployment; never edited at run time.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Changing the flag in the flag service changes what the next page load shows, with no
  restart, no deployment and no waiting period.
- **SC-002**: With the flag service stopped entirely, 100 percent of page loads still succeed and show
  the reason `service_unavailable`.
- **SC-003**: With the flag service hung, a page load completes within the configured wait plus render
  time, and never hangs with it.
- **SC-004**: For a partial rollout, the same user always gets the same outcome, and the split across
  many users lands within a few percent of the configured percentage — the consumer adds no randomness
  of its own.
- **SC-005**: A person who loads the page can state, from the page alone, which flag, environment and
  user produced the outcome and why — without reading a log or the source.
- **SC-006**: No page response and no page source ever contains the consumer's credentials.

## Assumptions

- The consumer page is a public product surface and requires no sign-in of its own; the `user`
  parameter identifies whom to evaluate for and is not an authentication claim. This is what makes the
  demo legible, and it is the reason the consumer holds no personal data and offers no write path.
- One instance represents exactly one environment. `dev` and `prod` are separate deployments of the
  same build, as they are for the flag service and the web app.
- The flag `new_banner` is the one the consumer renders; it is seeded by feature 001. A missing flag is
  an expected condition (`unknown_flag`), not an error.
- The wait ceiling for the flag service is short enough that a visitor never notices it; a default of
  about two seconds is assumed unless the plan finds a reason to differ.
- The page is plain HTML with a small amount of inline styling. There is no client-side application,
  no build step and no styling framework.
- Depends on feature 001 for evaluation and for the seeded flag. It does not depend on feature 002.
- Feature 001 accepts a second trusted issuer for service tokens (its FR-019, added by this feature).
  Until that lands, the consumer cannot authenticate at all — it is the first thing this feature builds.
- The consumer's key pair is generated per environment and delivered as configuration. Producing it in
  the cluster, encrypted, belongs to feature 005; locally it is generated on first run and gitignored.
