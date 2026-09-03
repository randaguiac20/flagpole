# Quickstart: 005-platform-delivery

What to run to see the feature work, and what each step proves. Run from the repository root.

## Prerequisites

`make bootstrap` has run once. Docker is running. Ports 80 and 443 are free — `scripts/ports.sh
check 80` says so, and `cluster-up` checks them itself before creating anything.

## 1. Build the images

```bash
make build
```

**Proves**: FR-001 and FR-002 — three images, non-root, every base pinned by digest, `hadolint`
clean. The script prints each resolved digest so a reader can see what was actually used.

## 2. Create the cluster and install the reconciler

```bash
make cluster-up
```

It stops and asks before the one step that changes anything outside this repository:

```
flux bootstrap github will:
  - commit Flux's own manifests to clusters/local/flux-system and push to origin/main
  - create a token-authenticated Secret in the cluster for randaguiac20/flagpole
Continue? [y/N]
```

It also creates the age key at `~/.config/sops/age/flagpole.agekey` if it does not exist, and applies
it as the `sops-age` Secret. **That file is the only copy** — losing it means re-encrypting every
secret in the repository.

**Proves**: FR-003, FR-004, FR-014 and FR-019.

## 3. Deploy

```bash
make deploy
```

Imports the images into the cluster, reconciles, and waits for readiness on a condition rather than a
sleep.

**Proves**: FR-005 and FR-020. `flux get kustomizations` then shows every unit applied, healthy, and
at a named revision (FR-007).

## 4. Look at it

Add nothing to `/etc/hosts`: `*.localhost` resolves to loopback on this machine (verify with
`getent hosts dev.flagpole.localhost`; the fallback line is printed if it does not).

- <https://dev.flagpole.localhost> — sign in as `alice@flagpole.local` / `flagpole`, change a flag
- <https://consumer.dev.flagpole.localhost> — the banner follows
- <https://prod.flagpole.localhost> — the other environment, with its own state

**Proves**: SC-002 and SC-008. Every host is served over TLS by a certificate the cluster issued, and
plain HTTP redirects to it.

## 5. Prove it is really GitOps

```bash
kubectl -n flagpole-dev scale deploy/flagpole-api --replicas=3   # refused by the hook; do it in the manifest
```

Change the replica count in `deploy/overlays/dev`, commit, push, then `flux reconcile kustomization
flagpole-dev --with-source`. The cluster follows. Delete a resource from the repository and it
disappears from the cluster.

**Proves**: FR-005, FR-006 and SC-003.

## 6. Prove it refuses what it should

```bash
scripts/verify-cluster.sh
```

Asserts the running cluster against `contracts/cluster-contract.json` and runs each refusal:

- a privileged Pod in an application namespace is rejected by the namespace, not by a reviewer
- a Pod in `flagpole-dev` cannot open a connection to `flagpole-prod`'s database
- the assistant's flag server writes in dev and is refused in prod

**Proves**: SC-005, SC-006 and SC-007.

## 7. End to end, in a browser

The Playwright suite cannot be pointed here: `frontend/playwright.config.ts` hardcodes
`baseURL: http://localhost:${WEB_PORT}` and starts its own Dex, API and web server, and `make e2e`
takes no target. Earlier drafts of this file and of task T043 said `make e2e TARGET=cluster`, which
never existed. Until the config takes a base URL, the cluster's acceptance evidence is gathered in a
browser against the ingress hosts, which is what the steps below do.

Trust the CA first (`docs/walkthrough.md` §"trust the cluster's CA" — all three trust stores; the
NSS step is the one browsers actually read).

1. Open `https://dev.flagpole.localhost`, sign in as `alice@flagpole.local` / `flagpole`.
   The header must show `operator`, not `viewer` — that claim comes from Dex and is the thing
   gotcha #49 broke silently.
2. Clear the `Enabled (dev)` checkbox on `new_banner` and press Save.
3. `curl -sS https://consumer.dev.flagpole.localhost/` → `enabled=false`, `reason=env_disabled`.
4. `curl -sS https://consumer.prod.flagpole.localhost/` → unchanged. Each namespace runs its own API
   and its own database, so a change made through the dev host cannot reach prod.
5. Re-check the box, Save, and confirm step 3 returns to `enabled=true`, `reason=rollout_hit`.
6. Open the audit log: both writes appear newest-first, attributed to `alice@flagpole.local`, as
   `on / 100% → off / 100%` and back.

**Proves**: SC-002 — a signed-in operator changes a flag through the cluster's ingress, the consumer
follows, the environments stay independent, and the change is attributable.

## Tearing it down

```bash
k3d cluster delete flagpole
```

The age key survives, because it lives outside the repository. Nothing else does — which is the
point.
