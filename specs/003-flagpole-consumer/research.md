# Research: 003-flagpole-consumer

Phase 0. Each item is a decision that was open when the plan started, with what it rules out.

## C1 — How a service proves who it is

- **Decision**: The consumer signs a short-lived RS256 token with its own private key. `flagpole-api`
  is configured with the matching public key under a second issuer name and validates that token the
  same way it validates a person's: signature, issuer, audience, expiry, subject.
- **Rationale**: The identity provider's discovery document lists `authorization_code`,
  `refresh_token`, `device_code` and `token-exchange` — no client-credentials grant, and no password
  grant either. Verified on 2026-09-02 against the running provider. So a service cannot obtain a
  token from it unattended. Signing our own keeps every request authenticated and reuses the
  `KeyResolver` seam that 001 already built to keep tests honest.
- **Alternatives**: a shared static secret (a second, weaker authentication path, long-lived, rotated
  by touching two services); making the evaluate endpoint unauthenticated behind a network policy
  (removes the control entirely in local development); giving the consumer a person's account (the
  provider supports no grant that would let it sign in unattended).

## C2 — Which claims the service token carries

- **Decision**: `iss` the configured service issuer, `sub` `flagpole-consumer`, `aud` the flag
  service's audience, `iat` and `exp` (five minutes), and **no `groups`**. A fresh token is minted per
  outbound call; there is no token cache.
- **Rationale**: No groups means the existing role rule in 001 — operator if the token names the
  operators group, viewer otherwise — grants the consumer viewer rights without a single new branch in
  the role check, which the spec requires to exist in exactly one place. Five minutes is short enough
  that a leaked token is nearly worthless and long enough to absorb clock skew. Minting per call costs
  microseconds and removes a cache and its invalidation.
- **Alternatives**: a long-lived token in configuration (a credential at rest that nothing rotates); a
  cached token with refresh (a cache, a clock and an expiry race, for no measurable gain).

## C3 — How `flagpole-api` decides which key to trust

- **Decision**: Read the token's `iss` claim without verifying, look it up among the configured trusted
  issuers, then verify fully with that issuer's key, audience and issuer pinned. An `iss` that is not
  configured is refused as unauthenticated, exactly like a bad signature.
- **Rationale**: Selecting a key by an unverified claim is safe when the selection can only choose
  among keys the operator configured, and the full verification that follows pins the issuer. This is
  how multi-issuer validation is normally done. The alternative — trying every configured key — turns
  one signature check into several and muddies the failure reason.
- **Alternatives**: trying each key in turn (slower, and the error becomes ambiguous); a separate
  endpoint or header for services (a second authentication path, which FR-011 exists to prevent).

## C4 — Where the key pair lives

- **Decision**: `scripts/consumer-keys.sh` generates `consumer/.keys/service.key` and `service.pub`
  for local development; the directory is gitignored. The paths are configuration. Feature 005 supplies
  the same pair as an encrypted secret and mounts it.
- **Rationale**: Keeps a private key out of the repository while letting `make dev` work with no
  ceremony. The generation script is idempotent, so it can run from `scripts/dev.sh` unconditionally.
- **Alternatives**: a committed test key (a private key in git, however harmless, teaches the wrong
  habit); generating a fresh pair at every start (the flag service's configured public key would go
  stale on every restart).

## C5 — What counts as a failure, and what happens then

- **Decision**: Connection errors, timeouts, any non-2xx answer, and any answer whose body is not the
  documented shape all collapse to the same outcome: `enabled = false`, reason `service_unavailable`,
  one log line at warning level naming the cause, HTTP 200. The timeout is a total ceiling
  (`httpx.Timeout`), default 2 seconds, configurable.
- **Rationale**: FR-007 asks for one behaviour, not five. Distinguishing them on the page would invite
  the visitor to act on the flag service's health, which is not their business; distinguishing them in
  the log is exactly what an operator needs, which is why the cause goes there and not on the page.
- **Alternatives**: a distinct reason per failure kind (the spec names one reason, and each extra value
  is another branch to test for no user-visible gain); retries (a hung upstream would multiply the
  visitor's wait, and this is a page load, not a background job).

## C6 — Readiness must not depend on the flag service

- **Decision**: `/healthz` and `/readyz` report only the consumer's own state. Neither calls the flag
  service.
- **Rationale**: If readiness failed during an upstream outage, the orchestrator would take the
  consumer out of service precisely when US2 says it must keep serving. This is the readiness mistake
  that turns one service's outage into two, and the spec calls it out as an edge case.
- **Alternatives**: a readiness probe that pings the flag service (turns a degraded page into no page).

## C7 — Rendering

- **Decision**: Jinja2 with autoescaping, two templates, inline CSS in the base template.
- **Rationale**: FR-014 requires everything from the request or the upstream answer to render as text.
  Autoescaping makes that the default rather than a discipline. Two templates and a few rules of CSS
  keep the page readable without a build step, which the non-goals rule out.
- **Alternatives**: f-string HTML (hand-escaping is the bug class this avoids); a styling framework or
  client-side app (excluded by the spec's non-goals, and neither earns its keep for one page).

## C8 — Testing every failure mode without a network

- **Decision**: `httpx.MockTransport` for the flag service, `httpx.ASGITransport` for the consumer app.
  Timeouts are simulated by a transport that raises `httpx.ReadTimeout`, never by sleeping.
- **Rationale**: The constitution forbids flaky and slow tests. A transport that raises makes the
  timeout path deterministic and instant, and `MockTransport` ships with httpx, so no test dependency
  is added for it.
- **Alternatives**: `respx` (a new dependency for something httpx already does); a live local server on
  a port (slow, racy, and it would fail differently on a busy machine).

## C9 — What the consumer does *not* get

Recorded so the next reader does not wonder: no cache of decisions (the spec forbids it, and it would
make US1's "the next load reflects the change" untrue), no retry, no circuit breaker, no database, no
sign-in of its own, no write path of any kind. If a real deployment later needed a cache, the signal
would be measured upstream load — not a hunch — and it would arrive with its own spec.
