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

## Measurements

Recorded during implementation; see the walkthrough for the output.
