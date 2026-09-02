# Implementation Plan: platform-delivery

**Branch**: `005-platform-delivery` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-platform-delivery/spec.md`

## Summary

Three container images, a k3d cluster whose ingress this project owns, and Flux bootstrapped from
this repository so that upgrading Flux is also a commit. Traefik, cert-manager and Dex arrive as
HelmReleases; PostgreSQL as a plain StatefulSet in each application namespace. One Kustomize base
plus two thin overlays produce `flagpole-dev` and `flagpole-prod`. Secrets are SOPS+age files in
git, decrypted by Flux with a key that never leaves the user's machine. Namespaces enforce the
restricted Pod Security Standard and a default-deny NetworkPolicy, so the isolation between the two
environments is enforced rather than asserted.

The one piece of application code this feature adds is a migration entry point that takes a
PostgreSQL advisory lock before running Alembic, so several replicas starting at once cannot race.

## Technical Context

**Language/Version**: no new language. Bash for the three scripts; YAML for manifests; one Python
module added to `backend/`

**Primary Dependencies**: k3d 5.9.0; Flux 2.9.5; Traefik chart 41.4.0 (app v3.7.12); cert-manager
chart v1.21.1; Dex chart 0.24.1 (app 2.44.0); `postgres:18-alpine`; `python:3.12-slim` and
`nginxinc/nginx-unprivileged:1.29-alpine` as image bases — every base pinned by digest

**Storage**: PostgreSQL 18 per environment, one `PersistentVolumeClaim` each, k3d's local-path
provisioner

**Testing**: `scripts/verify-cluster.sh` asserts the running cluster against
`contracts/cluster-contract.json`; `pytest` for the migration lock; `kubectl auth can-i` and a
deliberately non-conforming pod for the security assertions; `make e2e` against the cluster hosts

**Target Platform**: a k3d cluster on the developer's own machine, ports 80 and 443

**Project Type**: delivery and platform — no new service

**Performance Goals**: `make deploy` reaches all-ready within a few minutes on a cold cluster;
nothing here is a latency budget

**Constraints**: no sudo anywhere; nothing is applied into an application namespace by hand (the
GitOps hook already refuses it); no plaintext secret may be committed; ports are checked before they
are bound; anything touching GitHub or the host is announced first

**Scale/Scope**: two namespaces, three application workloads each, four platform components,
roughly forty manifests and three scripts

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Verdict |
|---|---|---|
| I. Spec is the source of truth | Behaviour traces to FRs; both settled questions are recorded as clarifications | **PASS** — the database topology and the bootstrap decision were answered and written into the spec before this plan |
| II. Simplicity and restraint | Fewest moving parts that satisfy the spec | **PASS** — a plain StatefulSet instead of a database operator, one chart per platform component, no service mesh, no image automation (006 owns it), no second cluster |
| III. Test-first and deterministic | Every behaviour has a check that fails first; no randomness, no sleeps | **PASS** — the cluster contract is asserted by a script, the migration lock has a unit test, and every wait is a `kubectl wait` on a condition rather than a sleep |
| IV. Security baseline | Least privilege; no secret in output | **PASS** — restricted Pod Security Standard enforced by the namespace, default-deny NetworkPolicy, non-root containers, secrets encrypted at rest in git, and the production overlay grants the assistant nothing |
| V. GitOps and reproducibility | Configuration, not code, per environment; rebuild from empty | **PASS** — Flux is bootstrapped from this repository and manages itself; the two environments differ only by overlay; `docs/BLUEPRINT.md` is re-run from an empty directory in phase 6 |

**Re-check after Phase 1 design**: unchanged. Two judgement calls are worth naming. First, the
production namespace is *not* a real production and the decision records say so; what is real is the
overlay boundary, the network policy and the absent operator grant. Second, `flux bootstrap` writes
to the remote repository and creates a deploy key — the script announces exactly that and stops for
an answer, because a command that changes something outside this repository should never be a
surprise.

## Project Structure

### Documentation (this feature)

```text
specs/005-platform-delivery/
├── plan.md                  # This file
├── research.md              # Phase 0 output
├── data-model.md            # Phase 1 output
├── quickstart.md            # Phase 1 output
├── contracts/
│   └── cluster-contract.json  # namespaces, hosts, units, workloads — asserted by a script
├── checklists/
│   └── requirements.md
└── tasks.md                 # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
backend/Dockerfile           # python:3.12-slim by digest, non-root, no build tooling in the runtime
consumer/Dockerfile
frontend/Dockerfile          # node build stage -> nginx-unprivileged, /config.js written at start
backend/app/migrate.py       # advisory lock, then alembic upgrade head
backend/tests/test_migrate.py

deploy/
├── base/                    # one copy of everything both environments share
│   ├── api/  consumer/  web/  postgres/
│   ├── networkpolicy.yaml   # default deny, then the allowances
│   └── kustomization.yaml
└── overlays/
    ├── dev/                 # namespace, hosts, replicas, the operator grant, the encrypted secrets
    └── prod/                # namespace, hosts, replicas, NO operator grant, its own secrets

platform/
├── traefik/  cert-manager/  dex/    # HelmRepository + HelmRelease each
└── issuer/                          # self-signed ClusterIssuer and the CA it signs with

clusters/local/
├── flux-system/             # written by flux bootstrap
├── platform.yaml            # Kustomization: platform, with dependsOn between components
├── flagpole-dev.yaml        # Kustomization: deploy/overlays/dev, decryption, healthChecks
└── flagpole-prod.yaml

scripts/
├── build.sh                 # the three images, digest-pinned bases, hadolint
├── cluster-up.sh            # ports, k3d create, age key, flux bootstrap (asks first)
├── deploy.sh                # import images, reconcile, wait for Ready
└── verify-cluster.sh        # assert the running cluster against the contract

.sops.yaml                   # encrypt only data/stringData, with the project's age recipient
```

## Complexity Tracking

| Addition | Why it is not avoidable | What was rejected |
|---|---|---|
| A migration entry point with an advisory lock | FR-012 requires the schema up to date before serving, and the spec's edge case forbids two starts running it twice. Alembic has no lock of its own | An init container calling `alembic` directly (races with more than one replica); a one-replica rule (dodges the requirement rather than meeting it); a separate migration Job per revision (a second reconciliation unit and an ordering problem, for the same guarantee) |
| A self-signed certificate authority | FR-010 requires TLS the cluster issued, and no public issuer can sign for `*.localhost` | Plain HTTP (fails FR-010); per-service self-signed certificates (a browser warning per host instead of one, and no chain to trust) |
| A StatefulSet per environment rather than one shared | The clarification: isolation the network can enforce, not just credentials | A shared instance with two databases (both namespaces must reach it, so the network policy proves nothing); an operator (a controller, its CRDs and its upgrade story, to run one database) |
| Two Dockerfiles for Python that look alike | The two services have different dependencies and different entry points; sharing a base image would add a fourth image to build and publish | A shared base image (a build-order dependency between images for perhaps twenty lines saved) |
