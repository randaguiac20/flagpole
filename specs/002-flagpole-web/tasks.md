# Tasks: Flagpole Web (login, flag table, audit log)

**Input**: Design documents from `/specs/002-flagpole-web/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-contract.md, quickstart.md; feature 001 merged (the API this UI talks to)

**Tests**: REQUIRED (constitution III, SC-004). Component tests with Vitest before each component; Playwright specs named after the acceptance scenarios.

**Organization**: by user story; each story is an independently testable increment.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup

- [ ] T001 Scaffold `frontend/` with `npm create vite@latest . -- --template react-ts --no-interactive` inside `frontend/`, then pin deps in `package.json`: react/react-dom 19.2, vite 8.2, typescript 5, oidc-client-ts 3.5, openapi-fetch 0.17; dev: openapi-typescript 7.13, vitest 4.1, jsdom 30, @testing-library/{react 16.3,dom 10.4,user-event 14.6,jest-dom 7}, @playwright/test 1.62; `npm install` and commit `package-lock.json`
- [ ] T002 [P] `frontend/vite.config.ts`: `server.port` from `FLAGPOLE_WEB_PORT` (default 18010), `strictPort: true`, `proxy: {"/api": {target: http://localhost:18000, changeOrigin: true, rewrite: p => p.replace(/^\/api/, "")}}`; `frontend/vitest.config.ts` with `environment: "jsdom"`, `globals: true`, setup file registering `@testing-library/jest-dom`
- [ ] T003 [P] `frontend/package.json` scripts: `dev`, `build`, `preview`, `test` (vitest run), `test:watch`, `api:types` (`openapi-typescript ../specs/001-flagpole-api/contracts/openapi.yaml -o src/api/schema.d.ts`), `api:types:check` (same with `--check`), `e2e` (`playwright test`), `lint` (`tsc --noEmit`)
- [ ] T004 [P] `dex/dev-config.yaml` and `docker-compose.dev.yaml` per research F5 (the ports are literals here because Dex reads a static file; keep them in sync with `docs/ports.md`) (image `ghcr.io/dexidp/dex:v2.45.1`, host port 18030, memory storage, `allowedOrigins: ["http://localhost:18010"]`, public client `flagpole-web` with redirect `http://localhost:18010/callback`, static users alice/operators and bob/viewers, `skipApprovalScreen`); add `docker compose ... up -d dex` and the web dev server to `scripts/dev.sh`, keeping the `scripts/ports.sh check` for every port
- [ ] T005 Generate `frontend/src/api/schema.d.ts` (`npm run api:types`) and commit it; add `npm run api:types:check` to `make test` so contract drift fails the build

## Phase 2: Foundational (blocking)

- [ ] T006 (FR-001, FR-003) `frontend/src/auth/userManager.ts`: `UserManager` with `authority` (`VITE_OIDC_ISSUER`), `client_id` (`VITE_OIDC_CLIENT_ID`), `redirect_uri` `${origin}/callback`, `scope: "openid profile email groups"`, `userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() })`; export `roleFromProfile(profile)` casting `groups` to `string[]` (FR-002)
- [ ] T007 [P] `frontend/tests/useSession.test.tsx`: role mapping (operators → operator, other groups/no groups → viewer), identity falls back to `sub`, `signOut()` clears the session, an `onUnauthenticated` call clears it (FR-002..004); run red
- [ ] T008 (FR-001, FR-003, FR-004) `frontend/src/auth/useSession.ts`: `{session, status, signIn, signOut, handleCallback, onUnauthenticated}`; sign-out is `removeUser()` + local clear (no `signoutRedirect`, research F2); run T007 green
- [ ] T009 [P] `frontend/tests/client.test.ts`: the client attaches `Authorization: Bearer` when a session exists, omits it otherwise, and calls `onUnauthenticated` on a 401 (FR-004, FR-014); run red
- [ ] T010 `frontend/src/api/client.ts`: `createClient<paths>({baseUrl: "/api"})` + middleware for the bearer token and the 401 hook; typed wrappers `listFlags`, `setEnvState`, `createFlag`, `listAudit`; run T009 green
- [ ] T011 [P] `frontend/src/components/Notice.tsx` + `frontend/tests/notice.test.tsx`: `notice-loading`, `notice-error` (with `notice-retry`), `notice-success` per contracts/ui-contract.md (FR-012, FR-013)

## Phase 3: User Story 1 — Sign in (P1)

**Independent test**: `frontend/tests/header.test.tsx` + `frontend/e2e/us1-signin.spec.ts`.

- [ ] T012 [P] [US1] `frontend/tests/header.test.tsx`: signed out → only `sign-in`, no flag data; signed in → `identity`, `role`, `sign-out` (US1-1..4); run red
- [ ] T013 [US1] `frontend/src/components/Header.tsx` and `frontend/src/App.tsx`: session-driven view selection, `/callback` handling via `signinRedirectCallback()` + `history.replaceState`, `onUnauthenticated` → signed-out screen with a notice (US1-5, FR-004); run T012 green
- [ ] T014 [US1] `frontend/e2e/us1-signin.spec.ts`: sign in as alice (operator) and bob (viewer) through the real Dex login form, assert `identity`/`role`, sign out, reload stays signed out

## Phase 4: User Story 2 — Flag table per environment (P1)

- [ ] T015 [P] [US2] `frontend/tests/flagTable.test.tsx`: rows ordered by key with key/description/enabled/rollout for the selected env; switching to `prod` re-renders every row from prod state and marks the tab `aria-selected`; API error shows `notice-error` with retry (US2-1..4, FR-005, FR-013); run red
- [ ] T016 [P] [US2] `frontend/src/components/EnvTabs.tsx` (`env-tab-dev`, `env-tab-prod`)
- [ ] T017 [US2] `frontend/src/components/FlagTable.tsx` + read-only `FlagRow` rendering; loading/error states; run T015 green
- [ ] T018 [US2] `frontend/e2e/us2-flag-table.spec.ts`: seed two flags through the API, sign in as bob, assert both rows and the tab switch

## Phase 5: User Story 3 — Operators change state, viewers cannot (P1)

- [ ] T019 [P] [US3] `frontend/tests/flagRow.test.tsx`: operator edits mark the row dirty (`flag-dirty-<key>`) and enable `flag-save-<key>`; save calls the API once and clears dirty; a refused save keeps the draft and shows the message in `flag-error-<key>`; rollout outside 0–100 or non-numeric blocks the request (US3-1,2,4, FR-006, FR-008, FR-009); run red
- [ ] T020 [P] [US3] `frontend/tests/viewerDisabled.test.tsx`: for a viewer session, `flag-enabled-*`, `flag-rollout-*`, `flag-save-*`, `create-*` are all `disabled` and exactly one `viewer-hint` is present (US3-3, US3-6, FR-007, SC-003); run red
- [ ] T021 [US3] Implement `frontend/src/components/FlagRow.tsx` (draft/saved per (flag, env), Save, disabled states) and `frontend/src/components/CreateFlag.tsx` (FR-015, conflict message); run T019+T020 green
- [ ] T022 [US3] `frontend/e2e/us3-operator-and-viewer.spec.ts`: as alice toggle `new_banner` to on/40 and save, assert the row and a new audit entry through the API; create `demo_flag` and assert both envs off/0; duplicate key shows the conflict message; as bob assert every write control disabled

## Phase 6: User Story 4 — Audit log (P2)

- [ ] T023 [P] [US4] `frontend/tests/auditList.test.tsx`: newest first with who/when/flag/env/before→after; a creation entry renders as "created"; filter narrows; `audit-load-more` appears only with a cursor and appends without duplicates (US4-1..4, FR-010, FR-011); run red
- [ ] T024 [US4] `frontend/src/components/AuditList.tsx`; run T023 green
- [ ] T025 [US4] `frontend/e2e/us4-audit.spec.ts`: after changes, assert order, filter and paging in the browser

## Phase 7: Polish & cross-cutting

- [ ] T026 `frontend/playwright.config.ts`: `webServer` array (API via `uv run uvicorn ... --factory`, Dex via docker compose, Vite dev server), `reuseExistingServer: !process.env.CI`, `use.baseURL` from `FLAGPOLE_WEB_PORT`, HTML reporter into `playwright-report/` with `open: "never"`; each spec seeds its own flags through the API so runs are order-independent (SC-005)
- [ ] T027 `frontend/src/styles.css` and basic accessibility: labels on every control, visible focus, table semantics; verify every `data-testid` in contracts/ui-contract.md exists in the DOM (FR-012); keep it to one stylesheet (constitution II)
- [ ] T028 [P] Run the whole suite: `npm run lint`, `npm test`, `npm run api:types:check`, `npx playwright test` (10 consecutive runs for SC-005); measure and record, never assert, the first-use sign-in time (SC-001) and the save round trip (SC-002) in `specs/002-flagpole-web/quickstart.md`
- [ ] T029 [P] Update `docs/dependencies.md` (frontend table), `docs/ports.md` (18010, 18030 confirmed), `docs/walkthrough.md` (002 row, `/e2e` skill and `ui-tester` agent runs with real output), `Makefile` (`make dev` starts Dex + API + web; `make e2e` runs Playwright)
- [ ] T030 Run the `code-reviewer` agent on the branch diff; fix findings; merge to `main`
