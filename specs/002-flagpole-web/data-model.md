# View models: 002-flagpole-web

No database. These are the shapes the UI holds; the persisted entities belong to 001.

## Session (in memory only, FR-003)

| Field | Type | Source |
|---|---|---|
| `accessToken` | string | `user.access_token` |
| `identity` | string | `user.profile.email ?? user.profile.sub` |
| `role` | `"operator" \| "viewer"` | `groups` claim contains `operators` (FR-002; same rule as the service) |
| `expiresAt` | number | `user.expires_at` |

`null` when signed out. Cleared by `signOut()` and by any `401` from the service (FR-004).

## FlagRow (per flag, per selected environment)

| Field | Type | Notes |
|---|---|---|
| `key`, `description` | string | from `GET /flags` |
| `saved` | `{enabled, rollout_percent}` | state of the selected environment as the service reports it |
| `draft` | `{enabled, rollout_percent}` | what the operator edited |
| `dirty` | boolean | `draft ≠ saved` → modified marker, Save enabled (US3-2) |
| `status` | `"idle" \| "saving" \| "error"` | with `message` on error (FR-009: the draft is kept) |

Rows are keyed by flag key and ordered by key (FR-005). Switching tabs re-derives `saved`/`draft` for the newly selected environment and discards nothing: unsaved drafts stay per (flag, env).

## AuditView

| Field | Type | Notes |
|---|---|---|
| `items` | `AuditEntry[]` | as served, newest first |
| `filterFlagKey` | string \| null | FR-011 |
| `nextBefore` | number \| null | cursor from the service; `null` hides "load older" |
| `status` | `"loading" \| "ready" \| "error"` | FR-013 |

An entry with `env === null` and `before === null` renders as "created" (FR-010).
