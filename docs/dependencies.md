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

## frontend (`frontend/package.json`, spec 002-flagpole-web)

| Package | Version | Why | Source |
|---|---|---|---|
| react, react-dom | 19.2.8 | UI runtime | https://react.dev |
| vite | 8.2.2 | dev server with the `/api` proxy and the production build | https://vite.dev |
| typescript | 5.9.3 | types; pinned to 5.x because `openapi-typescript` requires that peer | https://www.typescriptlang.org |
| oidc-client-ts | 3.5.0 | Authorization Code + PKCE in the browser, token held in memory | https://github.com/authts/oidc-client-ts |
| openapi-fetch | 0.17.0 | typed fetch client driven by the generated schema | https://openapi-ts.dev/openapi-fetch/ |
| openapi-typescript (dev) | 7.13.0 | generates `src/api/schema.d.ts` from the 001 contract; `--check` catches drift | https://openapi-ts.dev/cli |
| vitest, jsdom (dev) | 4.1.11, 30.0.1 | component tests | https://vitest.dev |
| @testing-library/{react,dom,user-event,jest-dom} (dev) | 16.3.3, 10.4.1, 14.6.7, 7.0.1 | user-centric component assertions (`dom` is a required peer of `react`) | https://testing-library.com |
| @playwright/test (dev) | 1.62.1 | end-to-end against the real identity provider | https://playwright.dev |
| oxlint (dev) | 1.79 | fast lint pass from the Vite template | https://oxc.rs |

## Container images

| Image | Tag | Why |
|---|---|---|
| ghcr.io/dexidp/dex | v2.45.1 | local OIDC provider for development and end-to-end tests (same version in the cluster in 005) |

## Consumer, MCP server, platform charts

Added by features 003–005.

## consumer (flagpole-consumer, 003)

| Package | Version | Why |
|---|---|---|
| fastapi | >=0.141,<1 | same framework as the API; one page and two health endpoints |
| jinja2 | >=3.1,<4 | autoescaped templates — FR-014 is a default here, not a discipline |
| httpx | >=0.28 | the one outbound call, and its `MockTransport` is what makes every failure testable |
| pyjwt[crypto] | >=2.13,<3 | signs the service token (RS256) |
| pydantic-settings | >=2.6,<3 | configuration that refuses an environment that cannot exist |
| prometheus-fastapi-instrumentator | >=8.1,<9 | `/metrics`, same shape as 001 |
| pytest, pytest-asyncio, ruff | dev | no `respx`: httpx ships the transport stub this needs |

No database, no cache, no client-side framework. The consumer holds nothing between requests.

## Cluster (feature 005-platform-delivery)

Charts and images pinned; Renovate proposes bumps in feature 006. Digests resolved 2026-09-02.

| Component | Version | Why | Source |
|---|---|---|---|
| k3d | 5.9.0 | one-command local cluster with a real load balancer on 80/443 | https://k3d.io |
| Flux | 2.9.5 | reconciles this repository; bootstrapped so its own upgrades are commits | https://fluxcd.io |
| traefik/traefik (chart) | 41.4.0 (app v3.7.12) | ingress; ingress-nginx is archived (gotcha #1) | https://traefik.github.io/charts |
| jetstack/cert-manager (chart) | v1.21.1 | the local certificate authority and the issued certificates | https://charts.jetstack.io |
| dex/dex (chart) | 0.24.1 (app 2.44.0) | OIDC with the same static users the dev stack uses | https://charts.dexidp.io |
| postgres | 18-alpine `sha256:d3e1620b…` | one per environment, plain StatefulSet | https://hub.docker.com/_/postgres |
| python | 3.12-slim `sha256:78387bc3…` | base for flagpole-api and flagpole-consumer | https://hub.docker.com/_/python |
| node | 24-alpine `sha256:e67514e5…` | build stage for flagpole-web | https://hub.docker.com/_/node |
| nginxinc/nginx-unprivileged | 1.29-alpine `sha256:0c79d56a…` | serves the web app; the ordinary nginx image binds :80 as root, which `restricted` rejects | https://hub.docker.com/r/nginxinc/nginx-unprivileged |
| ghcr.io/astral-sh/uv | 0.11.31 `sha256:ecd4de2f…` | uv copied from its published image rather than installed by a script | https://github.com/astral-sh/uv |
