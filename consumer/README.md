# flagpole-consumer

One page that shows what a feature flag actually does for a real user. Spec:
[`specs/003-flagpole-consumer`](../specs/003-flagpole-consumer/spec.md).

```
GET /                 the product page; ?user=<id> chooses whom to evaluate for
GET /healthz /readyz  unauthenticated, and they never call the flag service
GET /metrics          Prometheus, same shape as flagpole-api
```

## The thing that surprises people

**It decides nothing.** Every page load asks `flagpole-api` to evaluate `new_banner` for that user in
this instance's environment, and renders what it is told. There is no cache, no local copy of the
rule, and no fallback logic beyond one rule: if the answer does not arrive, show nothing new.

That is why a flag change appears on the very next load with no restart, and why a flag service
outage costs the banner rather than the page.

## How it authenticates

It signs its own short-lived token with a private key and presents it as a bearer token;
`flagpole-api` trusts the matching public key as a second issuer (001 FR-019). The token carries no
group membership, so the consumer is a viewer: it can evaluate and read, never write. The claim set is
fixed by [`contracts/service-token.md`](../specs/003-flagpole-consumer/contracts/service-token.md).

Generate the key pair once — it is gitignored, and the cluster gets its own:

```bash
scripts/consumer-keys.sh
```

## Running it

`make dev` starts everything. On its own:

```bash
cd consumer
FLAGPOLE_API_URL=http://127.0.0.1:18000 uv run uvicorn app.main:create_app --factory --port 18020
uv run pytest -q
```

Configuration is in [`data-model.md`](../specs/003-flagpole-consumer/data-model.md). An environment
that is not `dev` or `prod` stops startup rather than producing evaluations against an environment
that cannot exist.
