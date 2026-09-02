# Research: 002-flagpole-web

Sources fetched 2026-09-02 (npm registry, project docs, Dex source at v2.45.1).

## F1 — OIDC in the browser

- **Decision**: `oidc-client-ts` 3.5.0 with a plain `UserManager` wrapped in a small `useSession` hook. Settings: `authority` = issuer, `client_id`, `redirect_uri` = `<origin>/callback`, `scope: "openid profile email groups"`, `userStore: new WebStorageStateStore({ store: new InMemoryWebStorage() })`. `response_type` defaults to `code` and `disablePKCE` defaults to `false`, so PKCE is on without extra configuration.
- **Rationale**: FR-001/FR-003. Claims arrive as `user.profile`; `groups` survives claim filtering (the default filter list does not include it) but is typed `unknown`, so the role helper casts it to `string[]`.
- **Alternatives**: `react-oidc-context` 3.3.1 (nice `useAuth`, but adds a dependency and a mandatory `onSigninCallback` URL-cleanup gotcha); hand-rolled PKCE (crypto and state handling we would have to test ourselves).

## F2 — Sign-out

- **Decision**: sign-out calls `userManager.removeUser()` and clears local state; it does **not** call `signoutRedirect()`.
- **Rationale**: Dex v2.45.1 publishes no `end_session_endpoint` (verified in the release's discovery handler), and `oidc-client-ts` requires that metadata for `signoutRedirect()`. FR-003 only requires that the app forget the token.
- **Alternatives**: waiting for the Dex minor that adds RP-initiated logout (merged on `master`, unreleased) — recorded in `docs/gotchas.md` as the signal to revisit.

## F3 — Typed API client

- **Decision**: `openapi-typescript` 7.13 generates `src/api/schema.d.ts` from `specs/001-flagpole-api/contracts/openapi.yaml` (`npm run api:types`, and `--check` in CI to catch drift); `openapi-fetch` 0.17 provides the runtime client with `baseUrl: "/api"`.
- **Rationale**: FR-014 (documented API only) enforced by the compiler; the contract is already the 001 test's source of truth.
- **Alternatives**: hand-written types (drift); generating from the running service (build needs a server).

## F4 — Routing

- **Decision**: no router. `App.tsx` renders `SignedOut`, `Flags` or `Audit` from state; `window.location.pathname === "/callback"` triggers `signinRedirectCallback()` and then replaces the URL.
- **Rationale**: constitution II; two views, no deep links required by the spec.
- **Alternatives**: `react-router` 8 (a dependency and a mental model for two pages).

## F5 — Local identity provider

- **Decision**: `docker-compose.dev.yaml` runs `ghcr.io/dexidp/dex:v2.45.1` publishing container `5556` as host `18030`, config in `dex/dev-config.yaml`: `issuer: http://localhost:18030/dex`, `storage.type: memory`, `web.http: 0.0.0.0:5556`, `web.allowedOrigins: ["http://localhost:18010"]` (CORS covers `/token`, `/keys`, discovery — not `/auth`, which is a top-level navigation), `oauth2.responseTypes: ["code"]`, `oauth2.skipApprovalScreen: true`, `enablePasswordDB: true`, one `staticClients` entry with `public: true` and redirect URI `http://localhost:18010/callback`, and two `staticPasswords` with `groups`: `alice@flagpole.local` in `operators`, `bob@flagpole.local` in `viewers`.
- **Rationale**: real PKCE locally and deterministic end-to-end runs, offline. The same users and groups appear in the cluster in feature 005.
- **Alternatives**: pasted tokens in dev (no login path to test); cluster-only Dex (E2E blocked until 005).
- **Note**: bcrypt hashes contain `$`. The config is bind-mounted as a file, so compose never interpolates it and the hashes are written with a single `$`, exactly as `htpasswd` produced them. The demo passwords are not secrets and are documented in the quickstart.

- **Settled by the end-to-end run**: Dex puts `groups` in the *access* token, not only the id token. The
  browser derives the role from the id token profile while the service derives it from the bearer access
  token, so the two could disagree; US3-1 saves successfully as `alice`, which the service only allows for
  the `operators` group, proving the claim survives into the access token.

## F6 — Testing

- **Decision**: Vitest 4.1 with `environment: "jsdom"` for components (`@testing-library/react` 16.3 with an explicit `@testing-library/dom` dependency, `user-event`, `jest-dom`); Playwright 1.62 with a `webServer` array starting the API, Dex and the Vite dev server, `reuseExistingServer: !process.env.CI`, `use.baseURL` from the port table, HTML reporter into `playwright-report/` with `open: "never"`.
- **Rationale**: SC-004/SC-005; the suite must be startable with one command and deterministic.
- **Alternatives**: mocking the API in E2E (would not test the real contract); Cypress (Playwright is already the MCP browser).

## Version pins (npm registry, 2026-09-02)

vite 8.2.2 · react/react-dom 19.2.8 · typescript 5.x · oidc-client-ts 3.5.0 · openapi-typescript 7.13.0 · openapi-fetch 0.17.0 · vitest 4.1.11 · @testing-library/react 16.3.3 · @testing-library/dom 10.4.1 · @testing-library/user-event 14.6.7 · @testing-library/jest-dom 7.0.1 · jsdom 30.0.1 · @playwright/test 1.62.1 · dex image ghcr.io/dexidp/dex:v2.45.1. Lockfile is the source of truth; Renovate keeps them current.
