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
