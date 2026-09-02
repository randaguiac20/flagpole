# Dependencies

Every dependency: maintained upstream, pinned by `uv.lock` / `package-lock.json` / digest, scanned by `make scan` (pip-audit, osv-scanner, trivy). One line of justification each. Versions are the resolved ones at lock time; Renovate keeps them current.

## backend (`backend/pyproject.toml`, spec 001-flagpole-api)

| Package | Version | Why | Source |
|---|---|---|---|
| fastapi | 0.141.1 | HTTP framework with OpenAPI generation that the contract test diffs against | https://fastapi.tiangolo.com |
| uvicorn[standard] | 0.34+ | ASGI server for local dev and the container | https://www.uvicorn.org |
| sqlalchemy | 2.0.52 | ORM with typed mappings; same code on SQLite and PostgreSQL | https://www.sqlalchemy.org |
| alembic | 1.19.1 | Versioned schema migrations (FR-016) | https://alembic.sqlalchemy.org |
| pydantic | 2.13.5 | Request/response validation and the stable error shape | https://docs.pydantic.dev |
| pydantic-settings | 2.6+ | `FLAGPOLE_*` environment settings | https://docs.pydantic.dev/latest/concepts/pydantic_settings/ |
| pyjwt[crypto] | 2.13.0 | OIDC token validation with `PyJWKClient`; maintained, unlike python-jose | https://pyjwt.readthedocs.io |
| psycopg[binary] | 3.2+ | PostgreSQL driver for the cluster | https://www.psycopg.org/psycopg3/ |
| prometheus-fastapi-instrumentator | 8.1.0 | Request metrics on `/metrics` (FR-013) | https://github.com/trallnag/prometheus-fastapi-instrumentator |
| pytest, pytest-asyncio, httpx (dev) | 8+, 0.25+, 0.28+ | Async tests against the ASGI app, no network | official projects |
| ruff (dev) | 0.16.5 | Formatter + linter, also the PostToolUse hook | https://docs.astral.sh/ruff |
| pyyaml (dev) | 6+ | Reads `contracts/openapi.yaml` in the contract test | https://pyyaml.org |

## Tooling (installed via mise / uv tool, not in the repo)

flux2 2.9.5 · trivy 0.74.0 · hadolint 2.15.1 · osv-scanner 2.5.1 · yq 4.53.6 · sops 3.13.3 · age 1.3.1 · k3d 5.9.0 · specify-cli v1.0.3 · pip-audit 2.10.1 · bandit 1.9.4 · semgrep 1.176.0 · ruff 0.16.5 · gitleaks 8.30.1 · pre-commit hooks pinned in `.pre-commit-config.yaml`.

## Frontend, consumer, MCP server, platform charts

Added by features 002–005.
