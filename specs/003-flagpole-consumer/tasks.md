# Tasks: flagpole-consumer

**Feature**: `003-flagpole-consumer` | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)

Tests come first within each story (constitution III). `[P]` marks tasks that touch different files and
may run together.

## Phase 1: Setup

- [ ] T001 Create `consumer/pyproject.toml` (Python 3.12, uv): fastapi, jinja2, httpx, pyjwt[crypto], pydantic-settings, prometheus-fastapi-instrumentator, uvicorn; dev: pytest, pytest-asyncio, ruff. Mirror `backend/pyproject.toml`, including `ignore = ["B008"]`
- [ ] T002 [P] Add `scripts/consumer-keys.sh`: idempotently generate an RSA key pair into `consumer/.keys/{service.key,service.pub}`, chmod 600 the private key, print nothing secret; gitignore `consumer/.keys/` (FR-010a)
- [ ] T003 [P] Add consumer ports and settings to `.env.example` (`FLAGPOLE_CONSUMER_PORT=18020`, `FLAGPOLE_API_URL`, `FLAGPOLE_CONSUMER_TIMEOUT_SECONDS`, `FLAGPOLE_SERVICE_ISSUER`, `FLAGPOLE_SERVICE_AUDIENCE`, key paths) and to `docs/ports.md` if the row needs detail (FR-011)
- [ ] T004 [P] Extend `scripts/dev.sh`: generate the key pair if missing, export the service-issuer settings for the API, and start the consumer on `FLAGPOLE_CONSUMER_PORT` (FR-011)

## Phase 2: Foundational — the flag service learns to trust a service (001 FR-019)

**Blocks every consumer story: without it the consumer cannot authenticate at all.**

- [X] T005 `backend/tests/test_service_token.py`: a token from the configured service issuer evaluates a flag successfully; the same token is refused (403) on `POST /flags` and on `PUT /flags/{key}/env/{env}`; a token whose `iss` is not configured is refused (401); with no service issuer configured, a service token is refused (401). **Written first and failing.** (001 FR-019, FR-010c)
- [X] T006 `backend/app/config.py`: optional `service_issuer`, `service_audience` (default `flagpole-api`), `service_public_key_path`; unset issuer means the previous behaviour exactly (001 FR-019)
- [X] T007 `backend/app/auth.py`: resolve the trusted issuer from the token's unverified `iss`, then verify in full with that issuer's key, audience and issuer pinned; unknown issuer is unauthenticated. Add a `StaticPublicKeyResolver`. The role check stays untouched and in one place (001 FR-011, FR-019)
- [X] T008 Run the whole 001 suite: T005 green and the existing 37 tests still green (the amendment must not change behaviour when no service issuer is configured)

## Phase 3: User Story 1 — the flag changes what a visitor sees (P1)

**Independently testable**: with a flag service running, the banner appears and disappears with the flag.

- [ ] T009 [P] [US1] `consumer/tests/conftest.py`: app factory fixture, a throwaway key pair generated in-memory, and an httpx `MockTransport` stub for the flag service (supports FR-002, FR-007)
- [ ] T010 [P] [US1] `consumer/tests/test_page.py`: enabled answer renders `data-testid="banner"`; disabled answer does not; the request carries `Authorization: Bearer` and the documented body (`flag_key`, `env`, `user_id`). **Failing first.** (FR-001, FR-002, FR-004, FR-010)
- [ ] T010a [P] [US1] `consumer/tests/test_page.py`: two consecutive page loads make two upstream calls, and a changed answer is reflected on the second — the consumer keeps no cached decision and computes nothing itself (FR-003, SC-001). **Failing first.**
- [ ] T011 [P] [US1] `consumer/tests/test_tokens.py`: the minted token carries `iss`, `sub`, `aud`, `iat`, `exp` and **no** `groups`; expiry is five minutes; two calls mint two tokens. **Failing first.** (FR-010, FR-010b, FR-010c)
- [ ] T012 [US1] `consumer/app/config.py`: settings per data-model.md, refusing an environment that is not `dev` or `prod` and a timeout that is not positive (FR-011, FR-012)
- [ ] T013 [US1] `consumer/app/tokens.py`: sign the RS256 service token per `contracts/service-token.md` (FR-010, FR-010a, FR-010b)
- [ ] T014 [US1] `consumer/app/client.py`: one `POST /evaluate` with the bearer token and the configured timeout, returning a `Decision` (FR-002, FR-009)
- [ ] T015 [US1] `consumer/templates/base.html` + `page.html`: the banner and the decision panel, autoescaping on, inline CSS only (FR-004, FR-014)
- [ ] T016 [US1] `consumer/app/render.py` + `routers/page.py`: `GET /` with the optional `user` parameter and the default (FR-001, FR-004)
- [ ] T017 [US1] `consumer/app/main.py`: `create_app()` with a per-app metrics registry, the template environment, and settings on `app.state` — the same shape as 001 (FR-011)

## Phase 4: User Story 2 — the page survives a broken flag service (P2)

**Independently testable**: point the consumer at a dead address; the page still answers.

- [ ] T018 [P] [US2] `consumer/tests/test_failsafe.py`: connection error, read timeout, 500, 401, and a body of the wrong shape each produce `200`, no banner, reason `service_unavailable`. Timeouts are raised by the transport, never waited for. **Failing first.** (FR-007, FR-008, FR-009)
- [ ] T019 [US2] `consumer/app/client.py`: collapse every failure to the fail-safe decision; log one warning naming the cause; never raise into the request path (FR-007, FR-008)
- [ ] T020 [P] [US2] `consumer/tests/test_health.py`: `/healthz` and `/readyz` answer `ok` with the flag service unreachable, and neither makes an outbound call (FR-013)
- [ ] T021 [US2] `consumer/app/routers/health.py`: liveness and readiness that depend on nothing upstream (FR-013)
- [ ] T022 [P] [US2] `consumer/tests/test_config.py`: an unknown environment refuses to start; a non-positive timeout refuses to start; a missing key file refuses to start (FR-012)
- [ ] T022a [P] [US2] `consumer/tests/test_routes.py`: the application exposes exactly `/`, `/healthz`, `/readyz` and `/metrics`, all `GET` — there is no write path of any kind (FR-015). **Failing first.**

## Phase 5: User Story 3 — the decision is visible (P3)

**Independently testable**: two users at a partial rollout show different reasons on the page.

- [ ] T023 [P] [US3] `consumer/tests/test_page.py`: every anchor in `contracts/page-contract.md` is present; each reason value reaches `decision-reason` unchanged; a user containing HTML is escaped and does not alter the page structure. **Failing first.** (FR-005, FR-006, FR-014)
- [ ] T024 [US3] `consumer/templates/page.html`: the decision panel with all five anchors (FR-005)
- [ ] T025 [P] [US3] `consumer/tests/test_page.py`: the response never contains the token, the key, or the word `BEGIN PRIVATE KEY` (SC-006) (FR-008, SC-006)

## Phase 6: Polish and cross-cutting

- [ ] T026 `consumer/README.md`: what it is, how to run it, and the one thing that surprises people — it never decides anything itself
- [ ] T027 Verify every anchor in `contracts/page-contract.md` exists in the templates, and every claim in `contracts/service-token.md` is asserted by a test
- [ ] T028 Measure, never assert: record how long a page load takes with the flag service healthy and with it hung, and confirm the hung case ends at the wait ceiling rather than hanging (SC-003, constitution III). Run the quickstart by hand against a live flag service: US1 on and off, US2 with the service stopped, US3 for two users; record the real output in `quickstart.md`
- [ ] T029 `make test` and `make test-fast` include the consumer; `make dev` starts it; `docs/dependencies.md` gains the consumer's table
- [ ] T030 Add the 003 row to `docs/walkthrough.md` with real output, and a decision record if this feature introduced a Claude Code component (it should not — say so if not)
- [ ] T031 Run the `code-reviewer` agent on the branch diff; fix findings; merge to `main`

## Requirement coverage

Every functional requirement is cited by at least one task above; the citation is what makes coverage
checkable rather than assumed. `FR-003` and `FR-015` had no test until this analysis pass added T010a
and T022a — both are requirements that say the consumer must *not* do something, which is exactly the
kind that gets built correctly and then quietly regresses.

## Dependencies

```
Setup (T001-T004)
   └── Foundational (T005-T008)  ← blocks everything; the consumer cannot authenticate without it
          ├── US1 (T009-T017)    ← MVP
          ├── US2 (T018-T022)    ← independent of US3
          └── US3 (T023-T025)    ← independent of US2
                 └── Polish (T026-T031)
```

## Parallel opportunities

- T002, T003, T004 together (different files)
- T009, T010, T011 together (the US1 test files)
- T018, T020, T022 together (the US2 test files)
- US2 and US3 in either order once US1 is green

## Implementation strategy

**MVP is Phase 2 + Phase 3**: the flag service trusts the consumer, and the banner follows the flag.
That alone is the demonstration the whole product exists for. US2 makes it safe to deploy; US3 makes
it explicable. Each phase ends with its tests green and the previous phases still green.
