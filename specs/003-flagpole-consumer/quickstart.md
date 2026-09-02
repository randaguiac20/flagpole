# Quickstart: 003-flagpole-consumer

How to run the consumer and prove each user story by hand. The automated equivalents live in
`consumer/tests/`.

## Prerequisites

The flag service from 001, migrated and seeded, and a key pair for the consumer:

```bash
scripts/consumer-keys.sh                     # writes consumer/.keys/{service.key,service.pub}
cd backend && uv run alembic upgrade head && uv run python -m app.seed
```

The flag service needs to trust the consumer's key:

```bash
export FLAGPOLE_SERVICE_ISSUER=flagpole-consumer
export FLAGPOLE_SERVICE_AUDIENCE=flagpole-api
export FLAGPOLE_SERVICE_PUBLIC_KEY_PATH=../consumer/.keys/service.pub
uv run uvicorn app.main:create_app --factory --port 18000
```

Then the consumer, in another shell:

```bash
cd consumer && uv run uvicorn app.main:create_app --factory --port 18020
```

`make dev` does all of the above, including generating the key pair if it is missing.

## US1 — the flag changes what a visitor sees

```bash
curl -s localhost:18020/ | grep -c 'data-testid="banner"'        # 0: the seeded flag starts disabled
# turn it on for everyone in dev, as an operator, through the web app or the API
curl -s localhost:18020/ | grep -c 'data-testid="banner"'        # 1, on the very next load
```

## US2 — the page survives a broken flag service

```bash
# stop the flag service, then:
curl -s -o /dev/null -w '%{http_code}\n' localhost:18020/        # 200
curl -s localhost:18020/ | grep -o 'service_unavailable'         # the reason is stated
```

The consumer's log shows one warning naming the cause. `/readyz` still answers `ok` — the consumer is
healthy; its upstream is not.

## US3 — the decision is visible

```bash
curl -s 'localhost:18020/?user=alice@flagpole.local' | grep -o 'rollout_[a-z]*'
curl -s 'localhost:18020/?user=bob@flagpole.local'   | grep -o 'rollout_[a-z]*'
```

With `new_banner` at a partial rollout in `dev`, the two users can land on opposite sides, and the
banner follows the reason. Repeating either command gives the same answer every time — the consumer
adds no randomness, and the flag service's rule is deterministic.

## The 001 side

```bash
cd backend && uv run pytest tests/test_service_token.py -q
```

Proves a service token evaluates successfully and is refused when it tries to write.

## Measurements (2026-09-02, against live services)

```
$ cd consumer && uv run pytest -q
47 passed in 1.32s

$ cd backend && uv run pytest -q
46 passed in 2.20s          # 37 before this feature, plus 9 for the service issuer
```

US1, with the flag service running and `new_banner` enabled at 100% in dev:

```
banner elements: 1
decision-enabled = true
decision-reason  = rollout_hit
```

US3, the same flag at 50%, three users, then alice three times:

```
alice@flagpole.local     rollout_miss
bob@flagpole.local       rollout_hit
carol@flagpole.local     rollout_miss
alice again:  rollout_miss / rollout_miss / rollout_miss
```

US2, with the flag service stopped outright:

```
page:   http 200 in 0.050s
decision-reason = service_unavailable
banner elements: 0
readyz: {"status":"ok"}

consumer log:
  WARNING app.client flag evaluation failed, falling back to service_unavailable:
          ConnectError: All connection attempts failed
  occurrences of "Bearer" or "eyJ" in the log: 0
```

SC-003, against a server that accepts the connection and never answers, ceiling set to 2.0 s —
measured, not asserted (constitution III):

```
page: http 200 in 2.046s
page: http 200 in 2.034s
reason = service_unavailable
readyz during the hang: 200 in 0.0016s
consumer log: ReadTimeout
```

A healthy page load costs 0.033–0.047 s, so the ceiling is a ceiling and not a delay.

## After the code review

The reviewer returned 15 findings, 3 of them serious, each confirmed by running a probe. All are
fixed. Two changed the contract rather than only the code:

- A service token now names its environment (`env`), and the flag service refuses one minted for a
  different environment. Verified live: the same consumer that reads `env_disabled` from a `dev`
  service gets `service_unavailable` and a logged `401` when that service is told it serves `prod`.
- `contracts/service-token.json` is the machine-readable slice both suites assert against, so a
  drift in claim names, algorithm or lifetime fails a test instead of only the demo.

The bug worth naming: the consumer read the answer with `bool(body["enabled"])`, which treats the
string `"false"` as true. Typing the response was not enough — pydantic's ordinary coercion also
accepts `"yes"` — so the boundary uses a strict boolean, and five drifted shapes are tested.
