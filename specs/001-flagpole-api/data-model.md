# Data model: 001-flagpole-api

## Entities

### Flag (`flags`)
| Column | Type | Constraints | Spec |
|---|---|---|---|
| `key` | text, PK | `^[a-z][a-z0-9_]{1,62}$`, immutable | FR-001, FR-014 |
| `description` | text | ≤ 200 chars, may be empty | FR-001, FR-014 |
| `created_at` | timestamp (UTC) | set by the service on insert | FR-001 |

### FlagEnvironment (`flag_environments`)
| Column | Type | Constraints | Spec |
|---|---|---|---|
| `flag_key` | text, PK part, FK → `flags.key` (ON DELETE CASCADE, unused: no deletion) | | FR-002 |
| `env` | text, PK part | `dev` \| `prod` (enum in code and a CHECK constraint) | FR-002 |
| `enabled` | boolean | default false | FR-002 |
| `rollout_percent` | integer | 0–100 (CHECK) | FR-002, FR-004 |

Exactly two rows per flag, created in the same transaction as the flag (FR-002). Last write wins (FR-018): a plain `UPDATE`, no version column.

### AuditEntry (`audit_log`)
| Column | Type | Constraints | Spec |
|---|---|---|---|
| `id` | integer, PK autoincrement | cursor for pagination | FR-007 |
| `who` | text | token `email`, else `sub` | FR-005 |
| `at` | timestamp (UTC) | set on insert | FR-005 |
| `flag_key` | text, FK → `flags.key` | indexed (filter) | FR-005, FR-007 |
| `env` | text, nullable | null for creation entries | FR-005 |
| `before` | JSON text, nullable | `{"enabled":…, "rollout_percent":…}` or null for creation | FR-005 |
| `after` | JSON text | same shape; for creation: `{"description": …}` | FR-005 |

Append-only: no update/delete paths exist in the code.

### Caller (not persisted)
`identity: str` (email or sub), `role: Literal["viewer","operator"]` derived from `groups` containing `operators` (FR-012).

## Relationships

`Flag 1 — 2 FlagEnvironment` (composite PK `(flag_key, env)`); `Flag 1 — n AuditEntry`.

## State transitions

FlagEnvironment: `(enabled, rollout)` is set atomically by one `PUT`; any combination is valid (enabled at 0% means "on for nobody", disabled at 60% keeps the value for later). Creation: `flags` row + two `flag_environments` rows + one `audit_log` row in one transaction (FR-003, FR-005).

## Migration

`alembic/versions/0001_initial.py` creates the three tables, the CHECK constraints (`env IN ('dev','prod')`, `rollout_percent BETWEEN 0 AND 100`) and the index `ix_audit_log_flag_key_id (flag_key, id)`. SQLite and PostgreSQL both supported (no dialect-specific types; timestamps stored naive UTC).
