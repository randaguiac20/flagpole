# Contract: the consumer page

What `GET /` must contain. The end-to-end tests and the demo depend on these anchors; changing one is
a change to this spec.

## Request

| Part | Rule |
|---|---|
| `GET /` | always answers `200`, whatever the flag service does (FR-007) |
| `?user=<value>` | optional; blank or absent means `demo@flagpole.local` (FR-001) |
| any other query parameter | ignored |
| content type | `text/html; charset=utf-8` |

## Anchors in the page

| `data-testid` | Contains | Spec |
|---|---|---|
| `banner` | present **only** when the decision is enabled | FR-004 |
| `decision-flag` | the flag key | FR-005 |
| `decision-env` | `dev` or `prod` | FR-005 |
| `decision-user` | the user the decision was made for, escaped | FR-005, FR-014 |
| `decision-enabled` | `true` or `false` | FR-005 |
| `decision-reason` | one of `env_disabled`, `rollout_hit`, `rollout_miss`, `unknown_flag`, `service_unavailable` | FR-005, FR-006 |

## Health

| Path | Answer | Rule |
|---|---|---|
| `GET /healthz` | `{"status":"ok"}` | unauthenticated (FR-013) |
| `GET /readyz` | `{"status":"ok"}` | unauthenticated, and never calls the flag service (FR-013) |
| `GET /metrics` | Prometheus text | unauthenticated, same shape as 001 |

## Never in the response

The signing key, the token, the `Authorization` header, an internal address, or a stack trace — in the
body, in a header, or in an HTML comment (FR-008, SC-006).
