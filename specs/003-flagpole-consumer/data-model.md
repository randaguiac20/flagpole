# Data model: 003-flagpole-consumer

The consumer stores nothing. These are the shapes that exist for the length of one request, plus the
configuration it starts with.

## Decision (per request, never persisted)

| Field | Type | Where it comes from | Spec |
|---|---|---|---|
| `flag_key` | text | fixed: `new_banner` | FR-002, FR-005 |
| `env` | `dev` \| `prod` | configuration | FR-005, FR-011 |
| `user` | text | `user` query parameter, else `demo@flagpole.local` | FR-001 |
| `enabled` | boolean | the flag service's answer; `false` on any failure | FR-004, FR-007 |
| `reason` | text | the flag service's reason, or `service_unavailable` | FR-006, FR-007 |
| `from_service` | boolean | false when the fail-safe path produced it | FR-007 |

`reason` is one of `env_disabled`, `rollout_hit`, `rollout_miss`, `unknown_flag` (from the flag
service, passed through unchanged) or `service_unavailable` (the consumer's own). The consumer never
invents any other value and never rewrites one it was given.

**Invariant**: `enabled` is true only when `from_service` is true. There is no path that renders the
banner without an affirmative answer from the flag service (FR-003, FR-004).

## Consumer configuration (read once at start)

| Setting | Environment variable | Default | Rule |
|---|---|---|---|
| environment | `FLAGPOLE_CONSUMER_ENV` | `dev` | must be `dev` or `prod`, else the service refuses to start (FR-012) |
| flag service address | `FLAGPOLE_API_URL` | `http://localhost:18000` | — |
| wait ceiling | `FLAGPOLE_CONSUMER_TIMEOUT_SECONDS` | `2.0` | greater than zero (FR-009) |
| signing key path | `FLAGPOLE_CONSUMER_KEY_PATH` | `.keys/service.key` | must exist and be readable at start |
| service issuer | `FLAGPOLE_SERVICE_ISSUER` | `flagpole-consumer` | must match what the flag service trusts |
| audience | `FLAGPOLE_SERVICE_AUDIENCE` | `flagpole-api` | must match the flag service's expectation |

Configuration is read once. Nothing here is editable at run time, and none of it is rendered or logged
beyond the environment, the address and the timeout (FR-008, SC-006).

## Trusted issuer — the flag service's side (001 FR-019)

| Setting | Environment variable | Default | Effect |
|---|---|---|---|
| service issuer | `FLAGPOLE_SERVICE_ISSUER` | unset | when unset, the flag service behaves exactly as before |
| service audience | `FLAGPOLE_SERVICE_AUDIENCE` | `flagpole-api` | audience required in a service token |
| service public key | `FLAGPOLE_SERVICE_PUBLIC_KEY_PATH` | unset | PEM public key that verifies service tokens |

A token is matched to a trusted issuer by its `iss` claim, then verified in full against that issuer's
key, audience and issuer. An `iss` that names no configured issuer is refused as unauthenticated.

**Role**: unchanged and still decided in one place. A service token carries no `groups`, so it falls
through to viewer. Nothing in the role check knows that services exist.

**Audit**: a write is impossible for a service token, so no audit entry can name one. Should a future
feature grant a service write rights, `who` would record its `sub` (`flagpole-consumer`) exactly as it
records a person's email today.
