# Research: 005-platform-delivery

Phase 0. Each item is a decision that was open when the plan started, with what it rules out.
Versions were resolved on this host on 2026-09-02 and are recorded so a reader can tell what was
current rather than what was fashionable.

## E1 — Which ingress controller

- **Decision**: Traefik, chart `traefik/traefik` 41.4.0 (app v3.7.12), installed as a HelmRelease.
  k3d's bundled Traefik is disabled so that this project owns the one that runs.
- **Rationale**: PROMPT.md asked for ingress-nginx. That project was archived on 2026-03-24 and
  upstream now says not to deploy it, so following the prompt literally would install unmaintained
  software with no security fixes — gotcha #1. Traefik keeps plain `Ingress` resources working, so
  nothing else in the prompt changes. Disabling the bundled copy matters because otherwise two
  controllers claim the same Ingress and the winner depends on start order.
- **Alternatives**: ingress-nginx (archived); Envoy Gateway with the Gateway API (a larger change to
  every manifest and a second API to teach, recorded in `anti-patterns.md` as the future signal);
  k3d's bundled Traefik as-is (installed outside git, which defeats the whole feature).

## E2 — How Flux is installed

- **Decision**: `flux bootstrap github --token-auth --personal --owner randaguiac20 --repository
  flagpole --branch main --path clusters/local`, with Flux 2.9.5. The script prints the command and
  exactly what it will change outside this repository, then stops for an answer.
- **Rationale**: Bootstrapping commits Flux's own manifests into `clusters/local/flux-system`, so
  upgrading Flux is a commit like anything else. The alternative leaves the controllers installed by
  a command nobody records. The token comes from `gh auth token`; `--token-auth` then stores it as a
  Secret rather than generating an SSH deploy key, which is one fewer credential to explain.
- **Alternatives**: `flux install` plus a hand-applied GitRepository (nothing written to GitHub, but
  Flux is no longer managed from git — the user chose against it); SSH deploy key instead of a token
  (a second key to generate, store and revoke for a personal repository).

## E3 — Certificates for `*.localhost`

- **Decision**: cert-manager v1.21.1, a self-signed Issuer that mints one CA certificate, and a
  ClusterIssuer that signs every host from that CA. Traefik serves it and redirects HTTP to HTTPS.
- **Rationale**: No public authority will sign for `.localhost`, so the choice is between one local
  authority and none. One CA means one certificate to trust rather than one per host, and it
  demonstrates the chain that a real deployment would get from a public issuer.
- **Alternatives**: per-service self-signed certificates (a separate browser warning per host, and no
  chain); no TLS (FR-010); a public issuer with a real domain (a domain, a DNS challenge and an
  account, for a cluster that only ever answers on loopback).

## E4 — Identity in the cluster

- **Decision**: Dex chart 0.24.1 (app 2.44.0) as a HelmRelease, with the same static users the local
  development stack uses, at `dex.flagpole.localhost`.
- **Rationale**: The web app already reads its identity provider's address at runtime from
  `/config.js` (feature 002), so the same image serves both environments and neither is rebuilt to
  change issuer. Static users keep the demo self-contained; a real deployment would connect Dex to a
  real directory, and the decision record says so.
- **Alternatives**: Keycloak (a database, a realm import and far more surface for the same two
  users); reaching the development Dex from inside the cluster (the browser and the cluster would
  disagree about the issuer's address, which breaks token validation); no identity provider (there
  would be no roles to demonstrate).

## E5 — The database

- **Decision**: `postgres:18-alpine`, pinned by digest, as a plain StatefulSet with one
  PersistentVolumeClaim in each application namespace. Credentials come from a SOPS-encrypted Secret
  per environment.
- **Rationale**: The user chose one instance per environment so that isolation is enforced by the
  network rather than by credentials — a workload in one namespace cannot open a connection to the
  other's database, and SC-006 tests exactly that. A StatefulSet is about thirty lines; an operator
  is a controller, a set of custom resources and an upgrade story, to run one database that holds a
  handful of rows.
- **Alternatives**: one shared instance with two databases (both namespaces must reach it, so the
  network policy demonstrates nothing); an operator (out of proportion, and recorded in
  `anti-patterns.md`); keeping SQLite (no shared state between replicas, and it would dodge the
  migration and secret parts of the feature entirely).

## E6 — Running migrations exactly once

- **Decision**: `backend/app/migrate.py` takes a PostgreSQL advisory lock, runs `alembic upgrade
  head`, and releases it. It runs as an init container on the flag service, so the schema is current
  before the container that serves ever starts.
- **Rationale**: FR-012 wants the schema up to date before serving, and the spec's edge case forbids
  two simultaneous starts running it twice. Alembic has no lock of its own; an advisory lock is one
  round trip, is released automatically if the process dies, and needs no table of its own. An init
  container keeps the ordering inside the Pod, where Kubernetes already guarantees it.
- **Alternatives**: calling `alembic` directly from an init container (two replicas starting together
  race, and the loser fails in a way that looks like a broken image); pinning the flag service to one
  replica (dodges the requirement); a separate migration Job per revision (a second reconciliation
  unit, an ordering dependency and a naming scheme, for the same guarantee).

## E7 — Encrypting secrets

- **Decision**: SOPS 3.13.3 with age 1.3.1. `.sops.yaml` encrypts only `data` and `stringData` under
  `deploy/` and `clusters/`, so a review still shows which keys changed. The private key lives at
  `~/.config/sops/age/flagpole.agekey`; the cluster gets it as the `sops-age` Secret in
  `flux-system`, and each application Kustomization declares `decryption.provider: sops`.
- **Rationale**: Encrypting only the values keeps a diff reviewable, which is the difference between
  a secret store that people use and one they work around. Two guards already exist and are tested —
  a hook that refuses to write a plaintext Secret and a pre-commit check for edits made outside the
  session — so this feature supplies the key and the configuration, not the enforcement.
- **Alternatives**: encrypting whole files (an unreviewable diff); Sealed Secrets (a controller and a
  cluster-specific key, so the same file cannot be decrypted on the machine that wrote it); an
  external secret manager (a service, an account and a network dependency for a local cluster).

## E8 — One base, two overlays

- **Decision**: `deploy/base` holds everything both environments share. Each overlay sets the
  namespace, the hosts, the replica counts, the environment name and its own secrets. The production
  overlay additionally sets *nothing* for the assistant's operator grant, which is how FR-018 is met.
- **Rationale**: FR-008 asks for a change that applies to both to be made in one place. The overlays
  stay thin on purpose: the moment an overlay starts holding logic, the two environments have quietly
  become two systems.
- **Alternatives**: two full copies (drift, and the demo would teach it); Helm charts of our own (a
  templating language between the reader and the manifest, for two environments); one namespace with
  suffixed names (the namespace boundary is what the network policy acts on).

## E9 — Refusing what should be refused

- **Decision**: Each application namespace carries the restricted Pod Security Standard as an
  enforcing label, every container declares `runAsNonRoot`, a read-only root filesystem where the
  software allows it, and all capabilities dropped. A default-deny NetworkPolicy in each namespace is
  followed by the few allowances each workload actually needs.
- **Rationale**: FR-016 says the namespace must enforce it rather than trust it: a `securityContext`
  alone is a promise each manifest makes and a future manifest can forget, while the namespace label
  rejects the Pod outright. Default-deny first is the only ordering that fails safe — an allow-list
  built the other way round silently permits whatever nobody thought of.
- **Alternatives**: `securityContext` alone (nothing enforces it); an admission controller of our own
  (a webhook and its certificate, to restate a standard that ships with Kubernetes); no network
  policy (the isolation the user asked for would be a claim, not a control).

## E10 — Images

- **Decision**: `python:3.12-slim` for the two Python services and a `node:24-alpine` build stage
  serving from `nginxinc/nginx-unprivileged:1.29-alpine` for the web app — every base pinned by the
  digest resolved on 2026-09-02. Non-root, no build tooling in the runtime layer, `HEALTHCHECK`
  declared, and `hadolint` run over each.
- **Rationale**: FR-002 exists because a tag is a moving target: `python:3.12-slim` today and in six
  months are different software with the same name, and a digest makes the difference visible in a
  diff. `nginx-unprivileged` matters because the ordinary nginx image wants to bind port 80 as root,
  which the restricted standard rejects.
- **Alternatives**: distroless (a smaller surface, but no shell, which makes a demo cluster harder to
  inspect — the honest trade for a teaching repository); Alpine for Python (musl and wheels, a
  well-known source of confusing build failures); unpinned tags (FR-002).

## E11 — Supplying images to the cluster

- **Decision**: `scripts/build.sh` builds and tags locally; `scripts/deploy.sh` imports the images
  into k3d and then reconciles. The manifests name `ghcr.io/randaguiac20/flagpole-*` with a version
  tag and `imagePullPolicy: IfNotPresent`, so the same manifests work unchanged once feature 006
  publishes those images.
- **Rationale**: Feature 006 owns publishing and Renovate. Writing the manifests for the published
  name now means 006 changes a tag rather than a strategy.
- **Alternatives**: a local registry beside the cluster (another component to run and trust);
  `imagePullPolicy: Never` (works locally, then fails the moment the images are real).

## E12 — What this feature does *not* get

Recorded so the next reader does not wonder: no cloud, no second cluster, no service mesh, no image
automation (Renovate in 006), no horizontal autoscaling, no monitoring stack, no backup of the demo
database, no external secret manager, and no pretence that `flagpole-prod` is a production
environment. What is real about it is the overlay boundary, the network policy, the security standard
and the absence of the assistant's operator grant; the control plane is shared and the decision
records say so plainly.
