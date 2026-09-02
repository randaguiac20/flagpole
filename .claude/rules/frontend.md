---
paths:
  - "frontend/**/*.ts"
  - "frontend/**/*.tsx"
---

# Frontend (flagpole-web)

Loaded only when a TypeScript file under `frontend/` is read.

- React 19 function components + hooks, TypeScript `strict`. No `any`; use `unknown` and narrow.
- State that comes from the API lives in one place (`src/api/`), typed from the backend's OpenAPI schema. Components never call `fetch` directly.
- Auth: OIDC Authorization Code + PKCE against Dex, tokens kept in memory only (no `localStorage`). The Bearer token is attached in `src/api/client.ts` and nowhere else.
- Role gating is a prop (`canEdit`) derived from the `groups` claim; disabled controls stay visible so viewers see what operators can do.
- Every interactive element that an E2E test touches has a stable `data-testid`; tests never select by CSS class or text that may change.
- Tests: Vitest + Testing Library for units; Playwright for E2E. A component with logic has a unit test next to it (`Foo.test.tsx`).
- Vite env: only `VITE_`-prefixed, non-secret values. Client IDs are fine; client secrets never exist in this app (public PKCE client).
- Formatting: Prettier (PostToolUse hook runs it on the touched file).
