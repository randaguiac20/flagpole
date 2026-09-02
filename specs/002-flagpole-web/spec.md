# Feature Specification: Flagpole Web (login, flag table, audit log)

**Feature Branch**: `002-flagpole-web`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "Frontend: login (PKCE), flag table with dev/prod tabs (toggle + rollout slider, disabled for viewers), audit log." (PROMPT.md §4.1)

## Clarifications

### Session 2026-09-02

- Q: Should operators be able to create a flag from the web UI? → A: Yes, a small create form (key + description), operator only.
- Q: How are rollout changes applied? → A: Explicit Save per row; toggle and rollout edit locally, one request per saved row, modified marker on the row.
- Q: Which local sign-in setup does the frontend assume? → A: The demo identity provider runs locally in the dev stack (docker compose) with two static users (operator, viewer); end-to-end tests run against it.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Sign in with the organization's identity provider (Priority: P1)

A person opens Flagpole, is sent to the identity provider to sign in, and comes back signed in with their name and role visible. Signing out returns them to the signed-out screen.

**Why this priority**: Nothing in the UI is visible without an identity; the role decides what the rest of the UI allows.

**Independent Test**: Open the app signed out, sign in as a known user, see the user's identity and role; sign out.

**Acceptance Scenarios**:

1. **Given** a signed-out visitor, **When** they open the app, **Then** they see only a "Sign in" action and no flag data.
2. **Given** the visitor clicks "Sign in", **When** they authenticate at the identity provider as an operator, **Then** they return to the app and see their email and the role "operator".
3. **Given** a signed-in viewer, **When** they look at the header, **Then** the role shown is "viewer".
4. **Given** a signed-in user, **When** they click "Sign out", **Then** the app shows the signed-out screen and no flag data, and reloading keeps them signed out.
5. **Given** a signed-in user whose session has expired, **When** the next request is refused as unauthenticated, **Then** the app returns to the signed-out screen with a short notice instead of showing an error page.

---

### User Story 2 - See every flag's state per environment (Priority: P1)

A signed-in user sees all flags in a table, with tabs for `dev` and `prod`, showing for the selected environment whether each flag is enabled and its rollout percentage.

**Why this priority**: This is the read view every user needs; it is also the frame that operator controls live in.

**Independent Test**: With seeded flags, sign in as a viewer, switch tabs and compare the table with the API's flag list.

**Acceptance Scenarios**:

1. **Given** three flags exist, **When** a user opens the flags page, **Then** the table lists all three (key, description, enabled, rollout %) for the `dev` tab, ordered by key.
2. **Given** the `dev` tab is shown, **When** the user selects `prod`, **Then** every row shows the `prod` state and the selected tab is visibly marked.
3. **Given** a flag whose `dev` state is enabled at 25%, **When** the row is shown, **Then** the row reads "on" and "25%".
4. **Given** the API is unreachable, **When** the page loads, **Then** the user sees a retry notice, not a blank page.

---

### User Story 3 - Operators change a flag's state; viewers cannot (Priority: P1)

An operator toggles a flag on or off and sets its rollout percentage for the selected environment, then saves; the table shows the new state. A viewer sees the same controls disabled.

**Why this priority**: The write path is what the product is for; the viewer/operator difference is the authorization lesson made visible.

**Independent Test**: As an operator, change a flag's `dev` state and save; verify through the API. As a viewer, confirm the controls are disabled.

**Acceptance Scenarios**:

1. **Given** an operator on the `dev` tab, **When** they switch a flag on, set rollout to 40 and save the row, **Then** the row shows on/40%, the API reflects it, and a success notice appears.
2. **Given** an operator has changed a row but not saved, **When** they look at the row, **Then** it is marked as modified and the save action is enabled; other rows are unaffected.
3. **Given** a viewer, **When** they look at any row, **Then** the toggle, the rollout control and save are visible but disabled, with a hint that the operator role is required.
4. **Given** an operator whose save is refused by the API (for example the flag was removed or the input is invalid), **When** the refusal arrives, **Then** the row keeps the operator's pending values and shows the API's message.
5. **Given** an operator, **When** they create a new flag with a key and description from the flags page, **Then** it appears in the table with both environments off at 0%; a duplicate key shows the service's conflict message.
6. **Given** a viewer, **When** they look at the flags page, **Then** the create form is disabled with the operator-role hint.

---

### User Story 4 - Read the audit log (Priority: P2)

Any signed-in user can open the audit log and see who changed which flag, in which environment, from what to what, and when, newest first; they can narrow it to a single flag and load older entries.

**Why this priority**: Makes changes accountable; depends on flags having been changed.

**Independent Test**: After a few changes, open the audit page, check order and contents, filter by one flag, load the next page.

**Acceptance Scenarios**:

1. **Given** changes were made, **When** a user opens the audit page, **Then** entries appear newest first with who, when, flag, environment, before → after.
2. **Given** the audit page, **When** the user filters by a flag key, **Then** only that flag's entries are shown.
3. **Given** more entries than one page, **When** the user asks for more, **Then** older entries are appended without duplicates.
4. **Given** a creation entry (no environment, no "before"), **When** it is shown, **Then** it reads as "created" rather than showing empty fields.

### Edge Cases

- Rollout input outside 0–100 or non-numeric is rejected in the UI before any request is made.
- Keys are shown verbatim; descriptions longer than the column are truncated with the full text available on hover.
- Two tabs, never more: the environments are fixed by the service.
- The app never stores tokens in persistent browser storage; a page reload requires the identity provider to re-issue a session (silent if the provider still has one).
- A user with a token but no recognized role is a viewer.
- The app is usable at 1024 px wide and above; narrower layouts are out of scope.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST authenticate users through the organization's identity provider using the browser redirect flow for public clients (no client secret in the app).
- **FR-002**: After sign-in the app MUST display the user's identity (email) and role (`operator` or `viewer`) derived from the same rule the service uses (membership of the operators group).
- **FR-003**: The app MUST keep the session token in memory only; sign-out MUST clear it and return to the signed-out screen.
- **FR-004**: When the service answers "unauthenticated", the app MUST return to the signed-out screen with a notice.
- **FR-005**: The flags page MUST show all flags ordered by key with a tab per environment (`dev`, `prod`), showing enabled state and rollout percentage for the selected environment.
- **FR-006**: Operators MUST be able to change a flag's enabled state and rollout percentage for the selected environment and save the row explicitly; the app MUST call the service once per saved row and show the result.
- **FR-007**: For viewers, the same controls MUST be visible but disabled, with a hint that the operator role is required.
- **FR-008**: Rollout input MUST be validated in the UI to an integer 0–100 before a request is made.
- **FR-009**: A refused save MUST keep the user's pending values and show the service's message.
- **FR-010**: The audit page MUST list entries newest first with who, when, flag, environment, before and after; creation entries MUST be labelled as such.
- **FR-011**: The audit page MUST support filtering by flag key and loading older entries (cursor-based, no duplicates).
- **FR-012**: Every interactive element used by end-to-end tests MUST carry a stable test identifier.
- **FR-013**: Loading and error states MUST be explicit for every data view (flags, audit): a loading indicator, and an error notice with a retry action.
- **FR-014**: The app MUST work against the service's documented API only (`specs/001-flagpole-api/contracts/openapi.yaml`); it MUST NOT depend on undocumented fields.
- **FR-015**: Operators MUST be able to create a flag (key, description) from the flags page; the form is disabled for viewers; a refused creation shows the service's message.

### Key Entities

- **Session** (in memory): access token, identity (email), role, expiry.
- **FlagRow** (view model): key, description, per-environment state, pending edits, save status.
- **AuditEntry** (as served by the API): id, who, at, flag_key, env, before, after.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new user can sign in and see the flag table within 30 seconds on first use.
- **SC-002**: An operator can flip a flag and set its rollout in at most 3 interactions (toggle, rollout, save) and sees the result within 1 second on a local setup.
- **SC-003**: 100% of the write controls are disabled for viewers in every automated end-to-end run.
- **SC-004**: Every acceptance scenario above is covered by an automated test (unit or end-to-end) that fails when the behavior is removed.
- **SC-005**: The end-to-end suite is deterministic: 10 consecutive headless runs against the same seeded state produce identical results.

## Assumptions

- The identity provider is the demo's OIDC provider with two static users, an operator and a viewer; locally it runs in the dev stack started by `make dev`, and feature 005 deploys the same provider in the cluster.
- Single-page application served as static files by its own container in the cluster and by the dev server locally; it calls the service through a same-origin `/api` path (reverse proxy in both setups), so no cross-origin configuration is needed.
- No flag deletion or editing of key/description (not offered by the service).
- Access tokens expire per the identity provider's policy; there is no refresh flow in this feature (expiry returns the user to the signed-out screen, FR-004).
- Desktop browsers only; no localization; basic keyboard accessibility (focusable controls, labels).
