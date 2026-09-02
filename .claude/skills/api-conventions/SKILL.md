---
name: api-conventions
description: Reference for the Flagpole HTTP API - endpoint list, error shape, auth and role rules, pagination, naming, and versioning. Knowledge, not a workflow. Load when designing or reviewing an endpoint, writing an API client, or the MCP server.
user-invocable: false
---

# Flagpole API conventions (reference)

Source of truth for behavior is `specs/001-flagpole-api/spec.md`; this file records the *shape* conventions so every endpoint looks the same.

## Surface (nothing else exists)
| Method & path | Role | Purpose |
|---|---|---|
| `GET /flags` | viewer | list flags with both environments' state |
| `POST /flags` | operator | create `{key, description}`; both envs start disabled, rollout 0 |
| `PUT /flags/{key}/env/{env}` | operator | set `{enabled, rollout_percent}` for `env ∈ {dev, prod}`; writes an audit row |
| `POST /evaluate` | viewer | `{flag_key, env, user_id}` → `{enabled, reason}` |
| `GET /audit` | viewer | newest first, `?limit=` (default 50, max 200) `&before=<id>` cursor |
| `GET /healthz` `GET /readyz` `GET /metrics` | none | liveness, readiness (DB reachable), Prometheus |

## Shapes
- JSON only; `snake_case` field names; timestamps are RFC 3339 UTC strings (`created_at`).
- Errors: `{"detail": "<stable machine-readable sentence>"}` with the standard FastAPI status codes: 400 validation, 401 missing/invalid token, 403 role, 404 unknown flag, 409 duplicate key. Tests assert on `detail`.
- `flag_key`: `^[a-z][a-z0-9_]{1,62}$`. `rollout_percent`: integer 0–100. `env`: `dev|prod` (path param, validated as an enum).
- `reason` in `/evaluate` is one of: `env_disabled`, `rollout_hit`, `rollout_miss`, `unknown_flag` (→ `enabled=false`, HTTP 200, never 404: consumers must fail safe).

## Auth
- `Authorization: Bearer <JWT>` from Dex; validated against the issuer's JWKS (`PyJWKClient`), audience = the client ID, `alg` allowlist RS256.
- Role: `groups` claim contains `operators` → `operator`, else `viewer`. One dependency: `require_role("operator")`. `who` in the audit log is the token's `email`.
- Health/metrics endpoints are unauthenticated and excluded from the ingress auth requirements; `/metrics` is NetworkPolicy-restricted in the cluster.

## Versioning & compatibility
- No URL versioning in this demo. Additive changes only: new fields are optional with defaults; removing or renaming a field is a spec change with a new acceptance scenario.
- OpenAPI is generated (`/openapi.json`); the frontend types are produced from it, never hand-written.
