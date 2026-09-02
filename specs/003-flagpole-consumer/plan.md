# Implementation Plan: flagpole-consumer

**Branch**: `003-flagpole-consumer` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-flagpole-consumer/spec.md`

## Summary

A single server-rendered page that asks the flag service to evaluate `new_banner` for a given user in
this instance's environment, renders the banner only when the answer is enabled, and states the
decision it acted on. Every failure of the flag service — unreachable, slow, refusing credentials,
unreadable answer — produces the same safe outcome: a page without the banner, the reason
`service_unavailable`, a log line, and HTTP 200.

The consumer authenticates as itself with a short-lived token it signs with its own private key. That
requires the other half of this feature: `flagpole-api` learns to trust a second issuer for services
(001 FR-019), resolved through the `KeyResolver` abstraction it already has. Service tokens carry no
groups, so they are viewers and can evaluate but never write.

## Technical Context

**Language/Version**: Python 3.12, managed by uv (same toolchain as `backend/`)

**Primary Dependencies**: FastAPI; Jinja2 for the page (autoescaping on); httpx (async) for the one
outbound call; PyJWT[crypto] to sign the service token; pydantic-settings for configuration;
prometheus-fastapi-instrumentator for `/metrics`, consistent with 001

**Storage**: None. The consumer holds no database, no cache and no session — the decision lives for the
duration of one request

**Testing**: pytest with httpx `ASGITransport` for the app and httpx `MockTransport` for the flag
service, so every failure mode is exercised with no network and no sleeping

**Target Platform**: Linux container; locally `make dev` on port 18020

**Project Type**: Web service rendering HTML, plus an amendment to the existing `backend/` service

**Performance Goals**: A page load costs one upstream call. The wait for the flag service is capped at
2 seconds (configurable); nothing else in the request blocks

**Constraints**: Fail safe is absolute — no upstream condition may produce a non-200 page or an empty
page. Evaluation is never recomputed locally. No credential may reach the page or the log

**Scale/Scope**: One page, two health endpoints, one outbound call, roughly 300 lines of application
code plus templates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Verdict |
|---|---|---|
| I. Spec is the source of truth | Behaviour traces to FRs; a change to 001 is specified before it is written | **PASS** — 001 FR-019 and the superseded clarification were committed before this plan |
| II. Simplicity and restraint | Fewest moving parts that satisfy the spec | **PASS** — no cache, no database, no client-side app, no new test dependency (httpx's own `MockTransport` instead of `respx`), the key resolver in 001 is extended rather than replaced |
| III. Test-first and deterministic | Every failure mode has a test that fails first; no randomness, no sleeps | **PASS** — the outbound call is a stub transport, the timeout is asserted through a transport that raises rather than by waiting, and evaluation itself stays deterministic because the consumer never computes it |
| IV. Security baseline | Every request authenticated; least privilege; no secret in output | **PASS** — service tokens are short-lived, carry no groups, and therefore hold viewer rights; the private key is read from disk and never logged or rendered; SC-006 asserts it |
| V. GitOps and reproducibility | Configuration, not code, per environment | **PASS** — environment, upstream address, timeout and key paths are all configuration; the same image serves `dev` and `prod`; the service refuses to start on an unknown environment rather than misbehaving |

**Re-check after Phase 1 design**: unchanged. The design added no dependency and no persistence. The
one judgement call worth naming is that readiness deliberately ignores the flag service (FR-013): a
readiness probe that failed during an upstream outage would remove the consumer from service and
defeat US2, which is the whole point of the feature.

## Project Structure

### Documentation (this feature)

```text
specs/003-flagpole-consumer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── page-contract.md     # what the page must contain, for the tests and the demo
│   └── service-token.md     # the claim set 003 signs and 001 accepts
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
consumer/
├── pyproject.toml
├── app/
│   ├── main.py          # create_app(), instrumentator, template environment
│   ├── config.py        # Settings; refuses an environment that is not dev or prod
│   ├── tokens.py        # signs the short-lived service token (RS256)
│   ├── client.py        # the one call to flagpole-api; turns every failure into service_unavailable
│   ├── render.py        # Decision -> template context
│   └── routers/
│       ├── page.py      # GET /
│       └── health.py    # GET /healthz, /readyz
├── templates/
│   ├── base.html
│   └── page.html        # banner + decision panel
└── tests/
    ├── conftest.py      # app factory, stub transports, a throwaway key pair
    ├── test_page.py     # US1, US3
    ├── test_failsafe.py # US2, every upstream failure mode
    ├── test_tokens.py   # claim set, expiry, no key material in output
    ├── test_config.py   # refuses an unknown environment
    └── test_health.py   # readiness does not depend on the flag service

backend/                 # amended by this feature
├── app/
│   ├── auth.py          # trusted issuers resolved by the token's iss claim (FR-019)
│   └── config.py        # optional service issuer, audience and public key
└── tests/
    └── test_service_token.py  # a service token evaluates; the same token cannot write

scripts/
└── consumer-keys.sh     # generates consumer/.keys/{service.key,service.pub} for local dev
```

## Complexity Tracking

| Addition | Why it is not avoidable | What was rejected |
|---|---|---|
| A second trusted issuer in `flagpole-api` | The identity provider offers no client-credentials grant, and the consumer page has no signed-in user whose token could be forwarded | A shared static secret (a second, weaker authentication path); dropping authentication on the evaluate endpoint and relying on network policy (no control at all in local development) |
| A key pair for the consumer | Signing requires one. It is generated locally by a script and gitignored; the cluster gets it as an encrypted secret in feature 005 | Reusing the identity provider's key (would let the consumer mint tokens for people) |
| Jinja2 | Autoescaping is the requirement in FR-014, and hand-built HTML strings would have to reimplement it | f-strings (escaping by hand is exactly the bug this avoids); a client-side framework (a build step for one page) |
