# Quickstart: 002-flagpole-web

Prerequisites: Node 24, Docker (for the local identity provider), the API from feature 001, ports 18000/18010/18030 free (`scripts/ports.sh table`).

```bash
docker compose -f docker-compose.dev.yaml up -d dex   # Dex on :18030 (two static users)
cd frontend && npm ci
npm run api:types            # regenerate src/api/schema.d.ts from the 001 contract
npm run dev                  # Vite on :18010, proxying /api -> :18000
npm test                     # Vitest component tests
npx playwright test          # end-to-end, headless (starts API, Dex and Vite itself)
```

Demo users (local only, not secrets): `alice@flagpole.local` / `flagpole` in group `operators`, `bob@flagpole.local` / `flagpole` in group `viewers`.

| Scenario | How to check | Expect |
|---|---|---|
| US1 sign in | open `http://localhost:18010`, click Sign in, log in as alice | back on the app, `identity` = alice@flagpole.local, `role` = operator |
| US1 sign out | click Sign out, reload | signed-out screen, no flag data |
| US2 tabs | switch to `prod` | every row shows prod state, tab marked selected |
| US3 operator saves | toggle `new_banner`, set rollout 40, Save | row shows on/40%, success notice; `GET /audit` has a new entry |
| US3 viewer | sign in as bob | toggle, rollout, Save and the create form are disabled; one viewer hint |
| US3 create | key `demo_flag`, description, Create | row appears with both environments off at 0% |
| US4 audit | open Audit, filter by `new_banner`, load older | newest first, only that flag, no duplicates |

## Observed on 2026-09-02 (implementation session)

```
$ npm test                       # Vitest
Test Files 10 passed (10)  Tests  44 passed (44)  Duration ~1.0 s   (32 before the review)

$ npx playwright test            # starts API + Dex + Vite itself
9 passed (9.4s)

$ for i in $(seq 1 10); do npx playwright test; done      # SC-005
9 passed in every run (9.2-9.7 s)
```

Measured, not asserted (constitution III): first sign-in to flag table well under the 30 s of SC-001
(the whole 4-test sign-in spec runs in ~5 s including two full redirect round trips); a save round trip
(SC-002) completes inside the default 5 s expectation window, typically ~100 ms locally.

## After the code review (same day)

The suite grew with the fixes and the end-to-end run now starts from a database deleted at the start
of every run, so a fixed flag key is free each time:

```
$ make e2e                              # three consecutive runs
9 passed (11.1s) / 9 passed (9.5s) / 9 passed (9.5s)

$ FLAGPOLE_WEB_PORT=18011 make e2e      # the whole stack, Dex included, moves ports
9 passed (9.4s)
```
