# Tasks: platform-delivery

**Input**: Design documents from `/specs/005-platform-delivery/`

**Tests**: requested — the constitution requires a failing check before the behaviour exists. Here
most checks are assertions against a running cluster rather than unit tests, so `verify-cluster.sh`
is written before the manifests it verifies.

**Organization**: by user story, so each is independently completable and testable.

## Phase 1: Setup

- [X] T001 Write `scripts/verify-cluster.sh` reading `contracts/cluster-contract.json`, failing loudly against an empty cluster — the check exists before the thing it checks
- [X] T002 [P] Write `.sops.yaml`: encrypt only `data` and `stringData` under `deploy/` and `clusters/`, with the project's age recipient
- [X] T003 [P] Add `docs/secrets-sops.md`: generating the key, encrypting a file, rotating a value, what to do when the key is lost
- [X] T004 Add the cluster settings to `.env.example` (cluster name, hosts, image tag) and the host entries to `docs/ports.md`

## Phase 2: Foundational (blocking prerequisites)

- [X] T005 Write `backend/tests/test_migrate.py`: the lock is taken, a second caller waits and then finds nothing to do, and a dying process releases it
- [X] T006 Implement `backend/app/migrate.py` — advisory lock, `alembic upgrade head`, release (research E6)
- [X] T007 [P] Write `backend/Dockerfile`: `python:3.12-slim` by digest, non-root, no build tooling in the runtime layer, `HEALTHCHECK`
- [X] T008 [P] Write `consumer/Dockerfile` on the same pattern
- [X] T009 [P] Write `frontend/Dockerfile`: `node:24-alpine` build stage → `nginxinc/nginx-unprivileged:1.29-alpine`, `/config.js` written at container start from the environment
- [X] T010 Implement `scripts/build.sh`: build all three, print each resolved base digest, run `hadolint` over each Dockerfile
- [X] T010a Add a guard test asserting no Dockerfile names a base without a digest, so a later edit cannot unpin one silently (FR-002)
- [X] T011 Run `make build` and `make scan`; record every image's size and any finding in `docs/security-findings.md`

## Phase 3: User Story 1 — the whole product runs in the cluster (P1)

**Goal**: three documented commands take a clean machine to a working Flagpole in a browser.

**Independent test**: `make bootstrap && make cluster-up && make deploy`, then open the dev host and
change a flag.

- [X] T012 [US1] Implement `scripts/cluster-up.sh`: check ports 80 and 443, create the k3d cluster with the bundled ingress disabled, create the age key if absent, then **print what `flux bootstrap` will change outside this repository and stop for an answer** (FR-019)
- [X] T012a [US1] Occupy port 80, run `make cluster-up`, and show it refusing before anything is created, naming the listener (FR-004, edge case)
- [X] T013 [US1] Write `platform/traefik/` — HelmRepository and HelmRelease 41.4.0, pinned, ingress on 80 and 443
- [X] T014 [P] [US1] Write `platform/cert-manager/` — HelmRepository and HelmRelease v1.21.1 with CRDs
- [X] T015 [US1] Write `platform/issuer/` — self-signed Issuer, the CA Certificate, and the ClusterIssuer that signs each host
- [X] T016 [P] [US1] Write `platform/dex/` — HelmRepository and HelmRelease 0.24.1, static users, ingress at `dex.flagpole.localhost`, client secret from an encrypted Secret
- [X] T017 [US1] Write `clusters/local/platform.yaml` — the platform Kustomization with `dependsOn` between components and health checks
- [X] T018 [US1] Write `deploy/base/postgres/` — StatefulSet, Service, PersistentVolumeClaim, credentials from a Secret, and a `pg_isready` readiness probe (FR-020 covers every workload, not only the HTTP ones)
- [X] T019 [US1] Write `deploy/base/api/` — Deployment with the migration init container, Service, Ingress, probes on `/healthz` and `/readyz`
- [X] T020 [P] [US1] Write `deploy/base/consumer/` — Deployment, Service, Ingress, probes; readiness must not depend on the flag service (003 C6)
- [X] T021 [P] [US1] Write `deploy/base/web/` — Deployment, Service, Ingress, and the ConfigMap that becomes `/config.js`
- [X] T022 [US1] Write `deploy/overlays/dev/` and `deploy/overlays/prod/` — namespace, hosts, replicas, environment name; the operator grant in dev only (FR-018)
- [X] T023 [US1] Encrypt the four secrets with SOPS and confirm `git show` renders ciphertext for every value and plaintext for every key
- [X] T024 [US1] Write `clusters/local/flagpole-dev.yaml` and `flagpole-prod.yaml` — prune, wait, health checks, `decryption.provider: sops`, `dependsOn: platform`
- [X] T025 [US1] Implement `scripts/deploy.sh`: import the images into k3d, reconcile, and wait on conditions rather than sleeping
- [X] T026 [US1] Run `make cluster-up` and `make deploy`; show `flux get kustomizations` and `flux get helmreleases` all Ready (FR-007, SC-001)
- [X] T027 [US1] Open both environments in a browser: sign in, change a flag, see the consumer follow, and confirm each environment shows its own state (SC-002). Closed 2026-09-03: signed in through the ingress as `alice@flagpole.local`, cleared `Enabled (dev)` on `new_banner` and saved; `consumer.dev` went `true/rollout_hit → false/env_disabled` and back on re-enable, while `consumer.prod` stayed `false/env_disabled` throughout. Both writes are in the audit log against alice. The sign-in half was blocked by two things, not one: the self-signed CA (`--ignore-https-errors` for the MCP browser, and the NSS store for a human — gotcha #48) and Dex dropping the `groups` claim, which made every user a viewer who could not have changed anything (gotcha #49).

## Phase 4: User Story 2 — the cluster is changed only through git (P1)

**Goal**: every change is a commit, and a change made by hand does not survive.

**Independent test**: change a replica count in a manifest and watch the cluster follow; change it
back with `kubectl` and watch it disappear.

- [X] T028 [US2] Change a replica count in an overlay, commit, reconcile, and show the cluster following (FR-005, SC-003)
- [ ] T029 [US2] Change the same value directly in the cluster and show it reverted (FR-006). **Open, deliberately**: the gitops-guard hook refuses hand edits in every namespace but `flux-system` — stricter than the plan described — so demonstrating drift from inside a session would mean disabling the guard that makes the point. The command is printed in `docs/walkthrough.md` for the user to run.
- [X] T030 [US2] Remove a resource from the repository and show it pruned from the cluster (FR-006)
- [X] T030a [US2] Change one value in `deploy/base` and show both environments taking it from a single edit (FR-008)
- [X] T031 [US2] Show the GitOps hook refusing `kubectl apply` into an application namespace while allowing `flux-system`

## Phase 5: User Story 3 — secrets encrypted in git (P2)

**Goal**: the repository can be public and the passwords still private.

**Independent test**: read a committed secret — unreadable; read the same value in the cluster — the
one the application uses.

- [X] T032 [US3] Show a committed secret file: keys readable, values `ENC[...]` (FR-013, SC-004)
- [X] T033 [US3] Show the running application using the decrypted value, without printing it
- [X] T034 [US3] Attempt to commit a plaintext Secret and show both guards refusing it — the session hook and the pre-commit check (FR-015)
- [X] T035 [US3] Run `gitleaks detect` over the whole history and show it clean (SC-004)

## Phase 6: User Story 4 — the cluster refuses what it should (P3)

**Goal**: least privilege, enforced rather than promised.

**Independent test**: attempt each refused thing and see it refused.

- [X] T036 [US4] Add the restricted Pod Security Standard as an enforcing label on both application namespaces (FR-016)
- [X] T037 [US4] Add the default-deny NetworkPolicy and the allowances each workload needs (FR-017)
- [X] T038 [US4] Attempt a privileged Pod in an application namespace and show it rejected by the namespace (SC-005)
- [X] T039 [US4] Attempt a connection from `flagpole-dev` to `flagpole-prod`'s database and show it refused (SC-006)
- [X] T040 [US4] Point the assistant's flag server at each environment: it writes in dev and is refused in prod (SC-007, FR-018)
- [X] T041 [US4] Show every host answering over TLS with the cluster's certificate, and plain HTTP redirecting to it (SC-008)

## Phase 7: Polish & cross-cutting

- [X] T042 Run `scripts/verify-cluster.sh` green against the running cluster, and show it failing when a namespace is renamed
- [X] T043 Gather the acceptance evidence against the cluster hosts (`specs/005-platform-delivery/quickstart.md` §7). Rewritten 2026-09-03: this task said `make e2e TARGET=cluster`, and **no such target has ever existed** — `frontend/playwright.config.ts` hardcodes `baseURL` to localhost and starts its own stack, so the suite cannot be aimed at the cluster and a green `make e2e` says nothing about it (gotcha #50). Done as a browser run through the ingress instead, per T027. Pointing the suite at a base URL is a real gap; it is recorded in `docs/anti-patterns.md` rather than pretended away here.
- [X] T044 Run `make test` and `make test-hooks`; `shellcheck` clean on all three new scripts
- [X] T045 Write `docs/decisions/` entries for the cluster, the reconciler, the ingress choice, the secret handling and the database topology
- [X] T046 Update `docs/walkthrough.md` with real output for each success criterion
- [X] T047 Update `docs/anti-patterns.md` with what was deliberately not built (operator, mesh, second cluster, monitoring stack) and `docs/gotchas.md` with anything new
- [X] T048 Update `docs/dependencies.md` with the charts, images and their digests

## Dependencies

- Phase 1 → Phase 2 → Phase 3. Phases 4, 5 and 6 all need a running cluster, so they follow Phase 3;
  among themselves they are independent.
- T023 (encrypted secrets) blocks T024 and everything after: a Kustomization declaring decryption
  cannot reconcile without them.
- T012 stops for the user's answer. Nothing after it can run until that answer is given.

## Parallel opportunities

- T007, T008 and T009 are three separate Dockerfiles.
- T014 and T016 are separate platform components; T013 and T015 are not, because the issuer needs
  cert-manager's custom resources to exist.
- T020 and T021 are separate manifest directories.

## MVP scope

Phases 1–3. At that point the product runs in the cluster and is changed through git; the remaining
phases prove the properties that make it defensible rather than merely working.
