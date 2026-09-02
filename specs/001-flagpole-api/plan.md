# Implementation Plan: Flagpole API (flags, environments, evaluation)

**Branch**: `001-flagpole-api` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-flagpole-api/spec.md`

## Summary

A small HTTP service that stores flags with per-environment (`dev`/`prod`) state, evaluates them deterministically per user, and keeps an append-only audit log; OIDC bearer tokens from Dex decide identity and role. Approach: FastAPI + SQLAlchemy 2 + Alembic on SQLite (dev/tests) or PostgreSQL (cluster), PyJWT with a pluggable key resolver so tests sign their own tokens without any validation bypass, Prometheus metrics via the instrumentator plus one evaluation counter.

## Technical Context

**Language/Version**: Python 3.12 (pinned in `backend/.python-version`, managed by uv)

**Primary Dependencies**: FastAPI 0.141, SQLAlchemy 2.0, Alembic 1.19, Pydantic 2.13, pydantic-settings, PyJWT 2.13 `[crypto]`, psycopg 3 (PostgreSQL driver, cluster only), prometheus-fastapi-instrumentator 8.1, uvicorn

**Storage**: SQLite file for dev/tests (`FLAGPOLE_DATABASE_URL=sqlite:///./flagpole.db`), PostgreSQL 17 in the cluster (`postgresql+psycopg://…`, secret from SOPS in feature 005). Alembic migrations, one initial revision.

**Testing**: pytest, pytest-asyncio, httpx `AsyncClient` against the ASGI app, a temp SQLite file per test session, tokens signed with a test RSA key (see research R1). `ruff format` + `ruff check` in pre-commit/CI.

**Target Platform**: Linux container (non-root, digest-pinned base, feature 005); local `uvicorn` on port 18000 (`scripts/ports.sh`); `make dev` is completed by feature 002 (Dex in compose)

**Project Type**: web service (one of several in a monorepo: `backend/`)

**Performance Goals**: evaluation p95 < 50 ms locally (SC-006); nothing else is performance-sensitive (two demo users)

**Constraints**: deterministic evaluation (constitution III); no auth bypass (FR-011); no network in unit tests; single role-check dependency (FR-012); machine-readable error `detail` (FR-017)

**Scale/Scope**: ~10 flags, 2 environments, 2 users, audit log in the thousands at most; 9 endpoints; ~600 lines of application code

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status |
|---|---|---|
| I. Spec is the source of truth | Every module docstring cites `001-flagpole-api` + FR IDs; tests named after scenarios; plan changes → spec first | PASS (planned; enforced by `code-reviewer`) |
| II. Simplicity and restraint | Three entities, no repository layer, no service layer beyond `evaluation.py`; no deletion, no targeting rules | PASS |
| III. Test-first and deterministic | Tests written per FR before implementation tasks; SHA-256 bucket; no `random`; SQLite temp file; no network (key resolver injected) | PASS |
| IV. Security baseline | No plaintext secrets (none in this feature; DB URL from env); PyJWT with `algorithms=["RS256"]`, audience + issuer checks; one `require_role` dependency; `/metrics` unauthenticated but NetworkPolicy-restricted in 005 | PASS |
| V. GitOps and reproducibility | `make dev` uses `scripts/ports.sh`; seed idempotent; migrations versioned | PASS |

Post-design re-check (after Phase 1): unchanged, PASS. No Complexity Tracking entries.

## Project Structure

### Documentation (this feature)

```text
specs/001-flagpole-api/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R6
├── data-model.md        # Phase 1: entities, constraints, migration
├── quickstart.md        # Phase 1: how to run and prove it
├── contracts/
│   └── openapi.yaml     # Phase 1: HTTP contract (hand-written; the generated /openapi.json must match)
└── tasks.md             # /speckit-tasks output
```

### Source Code (repository root)

```text
backend/
├── pyproject.toml            # uv project: deps, ruff, pytest config
├── .python-version           # 3.12
├── alembic.ini
├── alembic/
│   ├── env.py                # reads FLAGPOLE_DATABASE_URL, targets app.models.Base
│   └── versions/0001_initial.py
├── app/
│   ├── __init__.py
│   ├── main.py               # create_app(): routers, instrumentator, lifespan (migrate? no: `make dev` migrates), error handlers
│   ├── config.py             # Settings (pydantic-settings): database_url, oidc_issuer, oidc_audience, oidc_jwks_url, env
│   ├── db.py                 # engine/session factory, get_session dependency
│   ├── models.py             # Flag, FlagEnvironment, AuditEntry (SQLAlchemy 2 typed mappings)
│   ├── schemas.py            # Pydantic request/response models, Env enum, Reason enum
│   ├── auth.py               # Caller, KeyResolver protocol, JwksKeyResolver, get_caller, require_role
│   ├── evaluation.py         # bucket(flag_key, user_id), evaluate(state, user_id) -> (enabled, reason)
│   ├── metrics.py            # flagpole_evaluations_total counter
│   ├── seed.py               # ensure_seed(session): new_banner, idempotent; `python -m app.seed`
│   └── routers/
│       ├── flags.py          # GET /flags, POST /flags, PUT /flags/{key}/env/{env}
│       ├── evaluate.py       # POST /evaluate
│       ├── audit.py          # GET /audit
│       └── health.py         # /healthz, /readyz
└── tests/
    ├── conftest.py           # app + temp SQLite + RSA test key + token factory (viewer/operator)
    ├── test_flags.py         # US1 scenarios, FR-001..005, FR-014, FR-018
    ├── test_evaluate.py      # US2 scenarios, FR-008..010, SC-002 distribution
    ├── test_audit.py         # US3 scenarios, FR-006, FR-007
    ├── test_auth.py          # FR-011, FR-012 (401/403, groups mapping, no-email → sub)
    ├── test_health.py        # US4, FR-013
    ├── test_seed.py          # FR-015 idempotency
    └── test_contract.py      # contracts/openapi.yaml ↔ app.openapi()
```

**Structure Decision**: single service under `backend/` (Option "web application" backend half; `frontend/` is feature 002). Routers are thin; the only domain logic lives in `evaluation.py` and the audit write inside the flags router; no repository/service layers (constitution II).

## Complexity Tracking

No violations. Table intentionally empty.
