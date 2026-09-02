# Quickstart: 001-flagpole-api

Prerequisites: `uv`, Python 3.12 (uv fetches it), port 18000 free (`scripts/ports.sh check 18000`).

```bash
cd backend
uv sync                                   # installs runtime + dev deps from uv.lock
uv run alembic upgrade head               # creates ./flagpole.db (FLAGPOLE_DATABASE_URL default)
uv run python -m app.seed                 # creates new_banner once (idempotent)
uv run pytest -q                          # all scenarios; no network, temp SQLite
uv run uvicorn app.main:create_app --factory --port 18000  # or: make dev (from repo root)
```

Prove the feature (with `make dev` running Dex on 18030; tokens from `scripts/dev-token.sh <user>` in feature 002/003 — until then use the test token factory):

| Scenario | Command | Expect |
|---|---|---|
| US4 liveness/readiness without a token | `curl -s localhost:18000/healthz; curl -s localhost:18000/readyz` | `{"status":"ok"}` twice |
| FR-011 unauthenticated refused | `curl -s -o /dev/null -w '%{http_code}' localhost:18000/flags` | `401` |
| US1 create + set dev 25% (operator token) | `curl -s -X POST localhost:18000/flags -H "Authorization: Bearer $OP" -d '{"key":"new_banner","description":"demo"}'` then `PUT /flags/new_banner/env/dev` with `{"enabled":true,"rollout_percent":25}` | 201 then 200; `GET /audit` shows 2 entries |
| US2 deterministic evaluation | `POST /evaluate {"flag_key":"new_banner","env":"dev","user_id":"alice"}` ×3 | identical `{enabled, reason}`; reason `rollout_hit`/`rollout_miss` |
| FR-010 unknown flag fails safe | `POST /evaluate {"flag_key":"nope","env":"dev","user_id":"x"}` | `200 {"enabled":false,"reason":"unknown_flag"}` |
| FR-012 viewer cannot write | `POST /flags` with `$VIEWER` | `403 {"detail":"operator role required"}` |
| FR-013 metrics | `curl -s localhost:18000/metrics \| grep flagpole_evaluations_total` | counter lines by `env`,`reason` |

Contract: `contracts/openapi.yaml` must match `curl localhost:18000/openapi.json` (a test diffs paths and status codes).

## Observed on 2026-09-02 (implementation session)

```
$ uv run pytest -q --durations=5
35 passed in 1.76s        # slowest: 0.16 s for 100 sequential /evaluate calls → ~1.6 ms each (SC-006 measured, not asserted)
$ uv run alembic upgrade head            # Running upgrade  -> 0001, initial
$ uv run python -m app.seed              # seeded new_banner   (second run: seed already present)
$ curl -s localhost:18000/healthz         # {"status":"ok"}
$ curl -s -o /dev/null -w '%{http_code}' localhost:18000/flags   # 401
```
