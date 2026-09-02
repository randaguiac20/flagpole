# Data model: 005-platform-delivery

This feature stores no new application data. What follows is the shape of the things it creates: the
environments, the units the reconciler keeps in step with this repository, and the secrets.

## Environment

Two, and the list is closed. Everything below is what an overlay sets; everything else comes from the
shared base.

| Field | dev | prod |
|---|---|---|
| namespace | `flagpole-dev` | `flagpole-prod` |
| web host | `dev.flagpole.localhost` | `prod.flagpole.localhost` |
| consumer host | `consumer.dev.flagpole.localhost` | `consumer.prod.flagpole.localhost` |
| replicas (api, consumer, web) | 1 | 2 |
| `FLAGPOLE_SERVICE_ENV` | `dev` | `prod` |
| operator grant for `flagpole-mcp` | set | **never set** (FR-018) |
| database | its own StatefulSet and volume | its own StatefulSet and volume |

Two replicas in production are not there for capacity; they exist so that the migration lock is
exercised by something rather than asserted (research E6).

## Reconciliation unit

A named group of manifests with its own health, revision and dependencies.

| Unit | Path | Depends on | Health is |
|---|---|---|---|
| `flux-system` | `clusters/local/flux-system` | — | the controllers are ready |
| `platform` | `platform/` | `flux-system` | every HelmRelease is ready |
| `flagpole-dev` | `deploy/overlays/dev` | `platform` | every workload is available |
| `flagpole-prod` | `deploy/overlays/prod` | `platform` | every workload is available |

Each application unit prunes (a resource removed from the repository is removed from the cluster),
waits for its health checks, and declares `decryption.provider: sops`.

## Platform component

| Component | Chart | Version | Gives |
|---|---|---|---|
| Traefik | `traefik/traefik` | 41.4.0 | the ingress this project owns, on 80 and 443 |
| cert-manager | `jetstack/cert-manager` | v1.21.1 | the certificate authority and the issued certificates |
| Dex | `dex/dex` | 0.24.1 | sign-in and the `groups` claim both environments read |

`platform/issuer/` holds the self-signed Issuer, the CA Certificate it mints, and the ClusterIssuer
that signs each host from that CA.

## Encrypted secret

A committed file whose structure is readable and whose values are not.

| Secret | Where | Holds |
|---|---|---|
| `flagpole-postgres` | each environment | the database user and password |
| `flagpole-service-keys` | each environment | the consumer's and the assistant server's public keys, and the consumer's private key |
| `dex-clients` | `dex` | the web application's client secret |
| `sops-age` | `flux-system` | the private key, **applied by the bootstrap script, never committed** |

`.sops.yaml` encrypts `data` and `stringData` under `deploy/` and `clusters/`, and nothing else, so a
review still shows which keys changed.

## Image

| Image | Base (pinned by digest, resolved 2026-09-02) | Runs as |
|---|---|---|
| `ghcr.io/randaguiac20/flagpole-api` | `python:3.12-slim` | non-root, read-only root filesystem |
| `ghcr.io/randaguiac20/flagpole-consumer` | `python:3.12-slim` | non-root, read-only root filesystem |
| `ghcr.io/randaguiac20/flagpole-web` | `node:24-alpine` build → `nginxinc/nginx-unprivileged:1.29-alpine` | non-root; writes `/config.js` at start |

## Migration lock

Not a stored entity, but the one piece of state this feature reasons about.

| Property | Value |
|---|---|
| Mechanism | PostgreSQL advisory lock, one fixed key for the whole schema |
| Held for | the duration of `alembic upgrade head` |
| Released by | the process, or by the connection closing if it dies |
| Result when a second process holds it | wait, then find nothing to do and exit successfully |
