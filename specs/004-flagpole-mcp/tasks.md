# Tasks: flagpole-mcp

**Input**: Design documents from `/specs/004-flagpole-mcp/`

**Tests**: requested — the constitution requires a failing test before the behaviour exists.

**Organization**: by user story, so each is independently completable and testable.

## Phase 1: Setup

- [X] T001 Create `mcp/flagpole-mcp/pyproject.toml` with Python 3.12, `mcp>=2.1.1`, `httpx`, `pyjwt[crypto]`, `pydantic-settings`, and a dev group with `pytest`, `pytest-asyncio`, `ruff`
- [X] T002 Create the package skeleton `mcp/flagpole-mcp/flagpole_mcp/__init__.py` and `mcp/flagpole-mcp/tests/__init__.py`
- [X] T003 [P] Add `mcp/flagpole-mcp/.keys/` to `.gitignore` and write `scripts/mcp-keys.sh` (idempotent RSA pair, private key chmod 600), mirroring `scripts/consumer-keys.sh`
- [X] T004 [P] Add the MCP settings to `.env.example` and register `flagpole-mcp` in `.mcp.json` with its command, args and environment
- [X] T005 Extend `Makefile` so `make test` runs the MCP suite and `make dev` exports `FLAGPOLE_OPERATOR_SERVICE_ISSUER`, and `scripts/dev.sh` calls `scripts/mcp-keys.sh`

## Phase 2: Foundational (blocking prerequisites)

- [X] T006 Write `mcp/flagpole-mcp/tests/test_config.py` asserting that an unknown environment refuses to start and a missing key path is reported at startup, not on first call (FR-014)
- [X] T007 Implement `mcp/flagpole-mcp/flagpole_mcp/config.py` — `Settings` per data-model.md, `env` restricted to `dev`/`prod`, key read once
- [X] T008 Write `mcp/flagpole-mcp/tests/test_tokens.py` asserting the minted token against `specs/003-flagpole-consumer/contracts/service-token.json` — algorithm, required claims including `env`, forbidden `groups`, 300-second lifetime
- [X] T009 Implement `mcp/flagpole-mcp/flagpole_mcp/tokens.py` — RS256 signer with `iss`/`sub` `flagpole-mcp`
- [X] T010 Write `mcp/flagpole-mcp/tests/conftest.py` — a throwaway key pair, the flag service as an httpx `MockTransport`, and the server under the SDK's in-memory `Client`
- [X] T011 Configure logging to stderr in `flagpole_mcp/__main__.py` and add a test asserting a tool call writes nothing to stdout (research D6)

### The flag service side (001 FR-020) — blocks US1's write path

- [X] T012 Extend `backend/tests/test_service_token.py`: a service token from the named operator issuer may write; the same token may not when the setting is unset; the viewer service issuer never may; naming the OIDC issuer or the viewer issuer is refused at startup
- [X] T013 Add `operator_service_issuer` to `backend/app/config.py` with the validator that refuses a collision (001 FR-020)
- [X] T014 Resolve the operator role for that one issuer in `backend/app/auth.py`, leaving the "groups on a service token are ignored" rule intact

## Phase 3: User Story 1 — an agent puts the system into a known state (P1)

**Goal**: three tools that read and change flag state through `flagpole-api`.

**Independent test**: set `new_banner` to enabled at 100 in dev through the server, read it back, and
see the new state.

- [X] T015 [P] [US1] Write `mcp/flagpole-mcp/tests/test_tools.py` for `list_flags` — every flag, both environments, an empty list when there are none
- [X] T016 [P] [US1] Add `get_flag` cases to `test_tools.py` — a known key, and an unknown key naming the key
- [X] T017 [P] [US1] Add `set_flag_state` cases to `test_tools.py` — a successful change, a rollout outside 0..100 naming the range, a bad key shape refused before any call, and `enabled="yes"` refused rather than coerced
- [X] T018 [US1] Implement `mcp/flagpole-mcp/flagpole_mcp/client.py` — the calls to the flag service, a fresh token per call, every failure mapped to its kind
- [X] T019 [US1] Implement the three tools in `mcp/flagpole-mcp/flagpole_mcp/server.py` with the names and arguments in `contracts/mcp-surface.json`
- [X] T019a [US1] Add a test asserting the server holds no state: two identical `get_flag` calls each reach the flag service, and a change made between them is visible on the second (FR-006)
- [X] T019b [US1] Add a source guard test asserting `flagpole_mcp/` contains no rollout arithmetic — no `sha256`, no `% 100` — so evaluation cannot quietly reappear here (FR-007)
- [X] T020 [US1] Write `mcp/flagpole-mcp/tests/test_contract.py` asserting the running server's surface matches `contracts/mcp-surface.json` — names, arguments, required flags

## Phase 4: User Story 2 — reading state without being told how (P2)

**Goal**: the resource and the prompt.

**Independent test**: read the flag-state resource without calling a tool; invoke the prompt and see
the flag's state embedded in it.

- [X] T021 [P] [US2] Write `mcp/flagpole-mcp/tests/test_resource_and_prompt.py` — the resource returns every flag in both environments, and the prompt contains the named flag's current state
- [X] T022 [US2] Implement the `flagpole://flags` resource in `server.py`
- [X] T023 [US2] Implement the `rollout_check` prompt in `server.py`, filling in the flag's current state

## Phase 5: User Story 3 — failing in a way an assistant can act on (P3)

**Goal**: every failure names its cause, and nothing leaks.

**Independent test**: stop the flag service and call each tool; each returns a message naming the
cause.

- [X] T024 [P] [US3] Write `mcp/flagpole-mcp/tests/test_failures.py` covering all six failure kinds in `contracts/mcp-surface.json`, each through a stub transport
- [X] T025 [US3] Add the assertion that no tool, resource or prompt output contains any string in `forbidden_in_any_output` (FR-010, SC-005)
- [X] T026 [US3] Make every capability total in `server.py` — no exception escapes; the `forbidden` kind says the server has not been granted operator rights, distinctly from an outage (FR-011a)

## Phase 6: Polish & cross-cutting

- [X] T027 Run `make test` and `make test-hooks`; `ruff format` and `ruff check` clean in `mcp/flagpole-mcp/`
- [X] T028 Run the quickstart end to end with `make dev`: set a flag through the server, see the banner on the consumer, and see `who = flagpole-mcp` in `GET /audit` (SC-001, SC-006)
- [X] T029 Start the server as a real process (`uv run python -m flagpole_mcp </dev/null`) and confirm it exits quietly (research D8)
- [X] T030 Write `docs/decisions/mcp-flagpole.md` — the decision test, including the honest note that a shell command would serve a human, and why the server exists anyway
- [X] T031 Update `docs/claude-code/mcp.md` and `docs/walkthrough.md` with real output for a tool, the resource and the prompt (SC-004)
- [ ] T031a Have the `ui-tester` agent arrange a Given state through this server and drive the browser, with no operator sign-in anywhere in the run (SC-002)
- [X] T032 Add any new gotcha discovered while implementing to `docs/gotchas.md`

## Dependencies

- Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6.
- T012–T014 (the flag service side) block T017's write case and all of Phase 6.
- US2 and US3 depend on US1's client, so they are not independently *implementable*, but each is
  independently *testable* once its phase completes.

## Parallel opportunities

- T003 and T004 are different files with no ordering between them.
- T015, T016 and T017 are separate test cases written against the same file; write them together and
  commit once.
- T021 and T024 touch different test files and may be written alongside their implementation phases.

## MVP scope

Phases 1–3. That is the whole reason the server exists: the `ui-tester` agent can arrange a Given
state. The resource and the prompt are what make it a server rather than a wrapper, and they follow.
