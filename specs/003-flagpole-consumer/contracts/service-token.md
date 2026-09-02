# Contract: the service token

Signed by `flagpole-consumer` (003), accepted by `flagpole-api` (001 FR-019). Changing anything here
is a change to both services and to both specs.

## Claims

| Claim | Value | Checked by the flag service |
|---|---|---|
| `iss` | the configured service issuer, default `flagpole-consumer` | must match a configured trusted issuer |
| `sub` | `flagpole-consumer` | required to be present; becomes the caller's identity |
| `aud` | the flag service's audience, default `flagpole-api` | must match exactly |
| `iat` | issue time | — |
| `exp` | issue time + 5 minutes | must be in the future |
| `env` | the consumer's environment, `dev` or `prod` | must match the flag service's own environment when it is configured |
| `groups` | **absent** | absent means no operator group, so the caller is a viewer |

Algorithm: **RS256**. The consumer holds the private key; the flag service is configured with the
public key only.

## Rules

1. A fresh token is minted for each outbound call. Tokens are not cached, stored, or logged.
2. The token appears only in the `Authorization: Bearer` header of the call to the flag service. It
   never appears in a page, a log line, an error message, or a metric label.
3. A service token grants viewer rights and nothing more. `POST /flags` and `PUT /flags/{key}/env/{env}`
   with a service token must be refused as forbidden — and there is a test that asserts it.
4. When the flag service has no service issuer configured, a service token is refused as
   unauthenticated, like any token from an unknown issuer.
5. A service token is bound to one environment. Without the `env` claim the only thing separating a
   `dev` token from a `prod` one would be the key pair, and nothing in the repository enforces that
   the two environments use different pairs. The claim makes the boundary explicit and checkable.
6. The flag service reads the public key once, at startup. A rotated key is picked up when the
   process restarts — which is what happens when the secret behind it changes in the cluster. Live
   reloading is deliberately not built; the signal that would justify it is a rotation policy that
   cannot tolerate a restart.

## Failure behaviour

Every refusal — expired, wrong audience, unknown issuer, bad signature — reaches the consumer as an
error answer, and the consumer treats it exactly like an outage: no banner, reason
`service_unavailable`, a log line naming the status. A credential problem must never be visible to a
visitor as an error page.
