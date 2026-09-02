# Feature Specification: Flagpole API (flags, environments, evaluation)

**Feature Branch**: `001-flagpole-api`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "001-flagpole-api: the Flagpole flag service API. Three concepts only: flags, environments, evaluation. …"

## Clarifications

### Session 2026-09-02

- Q: How should local development and automated tests authenticate, given real tokens come from Dex? → A: Tests sign their own tokens against a configurable issuer/key set; no validation bypass exists in the code; local dev uses the demo identity provider.
- Q: How does the consumer service (003) authenticate when evaluating on behalf of the logged-in user? → A: It forwards the user's own token; the evaluation endpoint sees a user identity, never a service identity. **Superseded 2026-09-02 while specifying 003** — see the amendment below.
- Q: Should the audit log be filterable by flag key in this feature? → A: Yes, an optional flag-key filter with unchanged pagination.
- Q: What happens when two operators change the same flag environment concurrently? → A: Last write wins; no version field; both changes are audited in order.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator manages a flag's rollout per environment (Priority: P1)

An operator creates a feature flag, then enables it in `dev` for a percentage of users, and later in `prod`. Every change is recorded so the team can see who changed what and when.

**Why this priority**: Without flags and per-environment state there is nothing to evaluate; this is the core write path and the source of every audit entry.

**Independent Test**: Create a flag, set its `dev` state to enabled/25%, read the flag list back, read the audit log. Delivers a usable flag service for one environment without any consumer.

**Acceptance Scenarios**:

1. **Given** an operator token, **When** they create flag `new_banner` with a description, **Then** the flag exists with both environments disabled at 0% and the response echoes the stored flag.
2. **Given** flag `new_banner` exists, **When** the operator creates it again, **Then** the request is rejected as a conflict and nothing changes.
3. **Given** flag `new_banner` exists, **When** the operator sets `dev` to enabled with rollout 25, **Then** the flag list shows `dev` enabled/25 and `prod` unchanged, and an audit entry records the operator, the time, the flag, the environment, the previous state and the new state.
4. **Given** an operator, **When** they set rollout to 101 or −1, or use environment `staging`, **Then** the request is rejected as invalid and no audit entry is written.
5. **Given** a viewer token, **When** they try to create a flag or change an environment state, **Then** the request is refused for insufficient role and no audit entry is written.
6. **Given** flag `new_banner` exists, **When** the operator sets `dev` to enabled/25 twice with identical values, **Then** the second call succeeds and writes a second audit entry with identical before/after (no de-duplication).

---

### User Story 2 - A consumer evaluates a flag for a user, deterministically (Priority: P1)

A consuming service asks "is `new_banner` on for user `u-42` in `prod`?" and gets a yes/no plus the reason. The same question always gets the same answer for the same flag state, so rollouts are stable per user and tests never flake.

**Why this priority**: Evaluation is the product; the consumer (feature 003) and the UI (002) both depend on it.

**Independent Test**: With a flag at `dev` enabled/50%, evaluate a fixed set of user IDs and compare against the documented bucket rule; repeat and expect identical results.

**Acceptance Scenarios**:

1. **Given** `new_banner` has `prod` disabled, **When** any user is evaluated in `prod`, **Then** the answer is disabled with reason `env_disabled`.
2. **Given** `new_banner` has `dev` enabled at 50%, **When** user `alice` is evaluated in `dev`, **Then** the answer is enabled or disabled exactly as the bucket rule says (bucket = the flag-and-user hash reduced to 0–99, enabled when bucket < rollout), with reason `rollout_hit` or `rollout_miss`.
3. **Given** the same flag state, **When** the same user is evaluated 100 times, **Then** all 100 answers are identical.
4. **Given** `dev` enabled at 100%, **When** any user is evaluated, **Then** the answer is enabled with `rollout_hit`; at 0% every user gets disabled with `rollout_miss`.
5. **Given** flag `does_not_exist`, **When** it is evaluated, **Then** the answer is disabled with reason `unknown_flag` and the request succeeds (consumers fail safe).
6. **Given** no token or an invalid token, **When** evaluation is requested, **Then** the request is refused as unauthenticated.

---

### User Story 3 - A viewer reads flags and the audit trail (Priority: P2)

Anyone with a valid login can list flags with both environments' state and read the audit log newest-first, but cannot change anything.

**Why this priority**: Read access is what the UI shows to every user and what makes the audit log useful; it depends on Story 1 having produced data.

**Independent Test**: With seeded data, list flags and read the audit log as a viewer; attempt a write and get refused.

**Acceptance Scenarios**:

1. **Given** three flags exist, **When** a viewer lists flags, **Then** all three are returned with `dev` and `prod` state each, ordered by key.
2. **Given** five audit entries exist, **When** a viewer reads the audit log, **Then** entries come newest first and each has who, when, flag key, environment, before and after.
3. **Given** more entries than the page size, **When** the viewer asks for the next page using the last entry as a cursor, **Then** the following entries are returned without gaps or duplicates.
4. **Given** entries for two flags, **When** the viewer filters the log by one flag key, **Then** only that flag's entries are returned, newest first.

---

### User Story 4 - The platform can tell whether the service is alive and ready (Priority: P3)

The cluster's probes and the monitoring stack need liveness, readiness and metrics without a login.

**Why this priority**: Required for deployment (feature 005) but not for using the service.

**Independent Test**: Call the three endpoints without a token; readiness fails when the data store is unreachable.

**Acceptance Scenarios**:

1. **Given** the service is running, **When** liveness is requested without a token, **Then** it answers OK.
2. **Given** the data store is reachable, **When** readiness is requested, **Then** it answers OK; **Given** it is unreachable, **Then** readiness answers not-ready.
3. **Given** requests have been served, **When** metrics are requested, **Then** request counts and latencies are exposed in the standard scrape format.

### Edge Cases

- A flag key that is not lowercase letters, digits and underscores (2–63 characters, starting with a letter) is rejected.
- A description longer than 200 characters is rejected; an empty description is allowed.
- Evaluation with an unknown environment value is rejected as invalid (unlike an unknown flag, which fails safe), because it indicates a consumer misconfiguration rather than a missing flag.
- A token that is valid but carries no email uses the token's subject as the audit identity.
- A token whose `groups` claim is absent is a viewer.
- The audit log is append-only; nothing in this feature can edit or delete an entry.
- Seed data (`new_banner`) is applied at most once; re-running the seed on an existing store changes nothing and writes no audit entry.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST store flags with a unique key, a description and a creation time.
- **FR-002**: Every flag MUST have state for exactly two environments, `dev` and `prod`: an enabled switch and a rollout percentage from 0 to 100, both starting disabled/0 when the flag is created.
- **FR-003**: Operators MUST be able to create a flag; creating a flag whose key already exists MUST be rejected as a conflict.
- **FR-004**: Operators MUST be able to set the enabled switch and rollout percentage of one environment of one flag in a single request; values outside 0–100 or unknown environments MUST be rejected with no side effects.
- **FR-005**: Every successful state change (FR-004) and every flag creation (FR-003) MUST append an audit entry with: who (the caller's identity from the token, email preferred, subject otherwise), when (field `at`), flag key, environment (empty for creation), state before and state after.
- **FR-006**: Any authenticated user MUST be able to list all flags with both environments' state, ordered by key.
- **FR-007**: Any authenticated user MUST be able to read the audit log newest first, paged with a default page size of 50, a maximum of 200, and a cursor on the last entry seen; an optional flag-key filter narrows the log to one flag without changing pagination.
- **FR-008**: Any authenticated user MUST be able to evaluate a flag for an environment and a user identifier and receive an enabled decision plus a reason.
- **FR-009**: Evaluation MUST be deterministic: if the environment is disabled the decision is disabled with reason `env_disabled`; otherwise a bucket 0–99 is derived from the flag key and user identifier using the documented hash rule (SHA-256 of `"<flag_key>:<user_id>"` reduced modulo 100) and the decision is enabled with `rollout_hit` when bucket < rollout, else disabled with `rollout_miss`.
- **FR-010**: Evaluating an unknown flag MUST succeed with decision disabled and reason `unknown_flag`.
- **FR-011**: All flag, evaluation and audit operations MUST require a valid token issued by one of the configured trusted issuers (each issuer's identity and signing keys are configuration, so tests can supply their own); there MUST be no switch that disables token validation. Missing or invalid tokens MUST be refused as unauthenticated.
- **FR-012**: The caller's role MUST be derived from the token's group membership: members of `operators` are operators, everyone else is a viewer; write operations by viewers MUST be refused as forbidden. The role check MUST exist in exactly one place.
- **FR-013**: Liveness, readiness and metrics MUST be available without a token; readiness MUST reflect whether the data store is reachable.
- **FR-014**: Flag keys MUST match `^[a-z][a-z0-9_]{1,62}$`; descriptions MUST be at most 200 characters.
- **FR-015**: The service MUST ship with an idempotent seed that creates the flag `new_banner` (both environments disabled) when it does not exist.
- **FR-016**: Data MUST survive restarts, and the schema MUST be versioned so that later features can change it without data loss.
- **FR-017**: Errors MUST carry a stable, machine-readable message so consumers and tests can rely on it.
- **FR-018**: Concurrent changes to the same flag environment are resolved last-write-wins; every accepted change is audited in the order it was applied, and no version token is required from callers.
- **FR-019**: A second trusted issuer MAY be configured for services rather than people. Tokens from it MUST be validated the same way as any other, MUST carry no group membership, and therefore MUST receive viewer rights only — a service can evaluate flags and read, never write. When no service issuer is configured, the service MUST behave exactly as before. A service token MUST also name the environment it was minted for, and MUST be refused when that environment differs from the one this service is configured for. (Added by 003-flagpole-consumer.)
- **FR-020**: One named service issuer MAY be granted operator rights by configuration. It is a
  second service slot with its own issuer name and its own key, distinct from the viewer service
  slot; it MUST be off unless explicitly set, and MUST be refused if it names the same issuer as the
  viewer slot or the identity provider. A service's role comes from the slot its issuer occupies and
  never from a claim in its token. Its writes are audited like anyone's, with
  the service named as the actor. (Added by 004-flagpole-mcp.)

### Amendment 2026-09-02 (from 003-flagpole-consumer)

- Q: The consumer page has no signed-in user to borrow a token from, and the identity provider offers
  no client-credentials grant. How does a service authenticate? → A: The service signs its own
  short-lived token with a private key, and this service validates it against a configured public key
  as a second trusted issuer. Service tokens carry no group membership, so they hold viewer rights and
  can evaluate but never change a flag.
- This supersedes the token-forwarding answer above, which assumed the consumer acted on behalf of a
  logged-in person. It does not weaken FR-011: every request still carries a token that is validated,
  and there is still no bypass. It adds FR-019 and widens FR-011 from one issuer to a configured set.

### Amendment 2026-09-02 (from 004-flagpole-mcp)

- Q: A service token grants viewer rights, but the flag-state server must write. How does it get
  permission? → A: One named service issuer may be granted operator rights by configuration
  (FR-020), off by default. The audit trail names the service, which is accurate: the assistant made
  the change, not a person. The alternative — the server holding a real operator's token — was
  rejected because it would record a person as the author of a change they did not make, and would
  expire in the middle of unattended runs.
- The operator service issuer is intended for local development. Nothing in the service enforces
  that; the boundary is that the production overlay never sets it (feature 005).

### Key Entities

- **Flag**: key (identity), description, created_at. Owns exactly two FlagEnvironment states.
- **FlagEnvironment**: flag key + environment (`dev` | `prod`), enabled, rollout_percent.
- **AuditEntry**: id (monotonic, used as cursor), who, when, flag key, environment (nullable for creation), before (nullable for creation), after.
- **Caller** (not stored): identity (email or subject) and role (`operator` | `viewer`) derived from the token.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator can create a flag and enable it for 25% of `dev` users in two requests, and see both changes in the audit log immediately.
- **SC-002**: For any fixed flag state, 1,000 evaluations of the same user return 1,000 identical answers; across 10,000 distinct users at rollout 50 the enabled share is between 45% and 55%.
- **SC-003**: Every write attempt by a viewer is refused and leaves no trace in the audit log (0 entries).
- **SC-004**: Every unauthenticated request to a flag, evaluation or audit operation is refused; liveness/readiness/metrics answer without a token.
- **SC-005**: A consumer asking about a flag that does not exist gets a safe "disabled" answer, not an error.
- **SC-006**: Evaluation answers in under 50 ms locally (p95) so consumers can call it on every page render. Measured (`pytest --durations`, reported in quickstart.md), never asserted in a test (constitution III forbids timing-based assertions).
- **SC-007**: Every functional requirement above has at least one automated test that fails when the behavior is removed.

## Assumptions

- Flag creation is audited (before = none) so the log answers "who introduced this flag"; the description did not say, and the audit log's purpose ("who changed what") suggests it.
- The identity provider is the demo's OIDC provider with static users; token validation details (issuer, audience, key discovery) are decided in the plan.
- Local development and tests use an embedded file-based store; the cluster uses a server database. The behavior is identical; only the connection differs.
- No flag deletion, no editing a flag's key or description after creation, no user management, no targeting beyond percentage rollout, no multi-tenancy, no UI (feature 002), no consumer (feature 003).
- Audit entries are never pruned in this demo.
- The consumer service (feature 003) forwards the end user's own token when evaluating; there is no service-to-service identity in this feature.
- No rate limiting; the service is local and the demo has two users.
- Percent rollout applies per (flag, user) pair; the same user may be in different buckets for different flags by design.
