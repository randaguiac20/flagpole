# Data model: 004-flagpole-mcp

This server owns no data (FR-006). What follows is the shape of what passes through it, and the
configuration it reads once at startup.

## Flag view (pass-through)

Returned by `list_flags`, `get_flag` and the flag-state resource. It is `flagpole-api`'s `FlagOut`
unchanged — the same field names, the same types — because a second model here would be a second
place to update when 001 changes.

| Field | Type | Notes |
|---|---|---|
| `key` | string | matches `^[a-z][a-z0-9_]{1,62}$` |
| `description` | string | up to 200 characters |
| `created_at` | string | ISO 8601, UTC, `Z` suffix |
| `environments` | object keyed by `dev` \| `prod` | each value `{enabled: bool, rollout_percent: 0..100}` |

An answer from the flag service that does not parse into this shape is the `unexpected_shape`
failure, not a partially-read result (FR-009).

## Tool arguments

| Tool | Argument | Type | Validated before any call |
|---|---|---|---|
| `get_flag` | `key` | string | key pattern |
| `set_flag_state` | `key` | string | key pattern |
| `set_flag_state` | `env` | `dev` \| `prod` | membership |
| `set_flag_state` | `enabled` | strict boolean | `"yes"` and `"false"` are refused, not coerced |
| `set_flag_state` | `rollout_percent` | integer | 0..100 inclusive |

`enabled` is strict on purpose. Ordinary coercion turns the string `"false"` into `True`, which would
enable a flag an assistant asked to disable — the failure would look like a working call.

## Failure

One shape for every failure, so the assistant reads it the same way each time.

| Field | Type | Notes |
|---|---|---|
| `kind` | one of `unreachable`, `unauthorized`, `forbidden`, `unknown_flag`, `invalid_argument`, `unexpected_shape` | the remedy differs per kind |
| `message` | string | names the cause and, for `unreachable`, the address tried |

No failure carries a token, a key or a traceback (FR-010).

## Service token (minted, never stored)

Exactly the claim set 003 defined, checked by both suites against
`specs/003-flagpole-consumer/contracts/service-token.json`, with `iss` and `sub` `flagpole-mcp` and
this server's own key pair. Minted per outbound call; there is no cache.

## Settings (read once at startup)

| Setting | Environment variable | Default | Notes |
|---|---|---|---|
| flag service address | `FLAGPOLE_API_URL` | `http://localhost:18000` | named in the `unreachable` message |
| environment | `FLAGPOLE_MCP_ENV` | `dev` | must be `dev` or `prod`, else refuse to start (FR-014) |
| private key path | `FLAGPOLE_MCP_KEY_PATH` | `mcp/flagpole-mcp/.keys/service.key` | read once; never logged |
| issuer | `FLAGPOLE_MCP_SERVICE_ISSUER` | `flagpole-mcp` | must match what the flag service was told |
| audience | `FLAGPOLE_MCP_SERVICE_AUDIENCE` | `flagpole-api` | |
| timeout | `FLAGPOLE_MCP_TIMEOUT_SECONDS` | `5.0` | total ceiling per upstream call |

## Added to `flagpole-api` by this feature (001 FR-020)

| Setting | Environment variable | Default | Notes |
|---|---|---|---|
| operator service issuer | `FLAGPOLE_OPERATOR_SERVICE_ISSUER` | unset | when set, tokens from that one service issuer resolve to `operator`; refused if it names the OIDC issuer or the viewer service issuer |
| operator service key | `FLAGPOLE_OPERATOR_SERVICE_PUBLIC_KEY_PATH` | unset | the public key for that slot; read at startup so a misconfigured deployment fails loudly |
