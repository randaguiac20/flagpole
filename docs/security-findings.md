# Security findings

Every finding the scanners report at or above its failing threshold is recorded here with a
decision, a reason and a date. This is not a log — it is the only way past a scanner. `scripts/scan.sh`
reads this file: a finding with a row no longer fails the run, and a finding without one does.

Spec: `specs/006-ci-and-security/` (FR-012). Format: `specs/006-ci-and-security/data-model.md`.

## Failing thresholds

| Scanner | Covers | Fails the run at |
|---|---|---|
| `gitleaks` | secrets in the tree and its history | **any** finding — a leaked credential is never a judgement call |
| `hadolint` | the three Dockerfiles | `error` |
| `bandit` | Python source | `HIGH` |
| `semgrep` | Python and TypeScript source | `ERROR` |
| `pip-audit` | Python dependencies | `HIGH` |
| `npm audit` | npm dependencies | `high` |
| `osv-scanner` | every lockfile | `HIGH` |
| `trivy` | images and Kubernetes manifests | `HIGH` |

Anything below its threshold is printed and does not fail. It still deserves a row if someone
decided something about it.

## Rules

- **A row is never deleted.** A `fixed` row stays as the record that it was once true.
- **`accepted` and `not applicable` need a reason that names why** — why the code is not reachable,
  or why the risk is tolerable here. "Low priority" is not a reason.
- **`deferred` needs a condition that ends it**, not a date that slips. "Until the chart publishes
  a release with the fix" is a condition; "next quarter" is not.
- **`fixed` means the finding is gone**, verified by re-running the scanner — not that a change was
  made in its direction.

## Findings

`deferred` rows below name the condition that ends them, never a date. Both are waiting on the same
thing: an upstream base image rebuilt with packages that already carry the fix. Renovate's
`dockerfile` manager proposes the digest bump when that happens, which is the mechanism that closes
them — see `docs/renovate.md`.


| Date | Scanner | Identifier | Severity | Where | Decision | Reason |
|---|---|---|---|---|---|---|
| 2026-09-02 | trivy | CVE-2026-14456, CVE-2026-33630, CVE-2026-45186, CVE-2026-45447, CVE-2026-56408, CVE-2026-5773, CVE-2026-6276, CVE-2026-66046, CVE-2026-6732, CVE-2026-76641 | HIGH/CRITICAL | `nginxinc/nginx-unprivileged:1.29-alpine@sha256:0c79d56a…` — `c-ares`, `libcurl`, `libexpat`, `libssl3`, `libxml2` | deferred | Alpine has published fixed packages for all ten; the base image has not been rebuilt with them. `1.29-alpine` today still resolves to the digest pinned here, so there is no newer image to move to. **Ends when** the tag resolves to a rebuilt digest — Renovate's `dockerfile` manager proposes that bump, and this row goes with it. Not `accepted`: nothing about this is tolerable, it is merely not yet available. |
| 2026-09-02 | trivy | CVE-2026-14257, CVE-2026-14456, CVE-2026-69152, CVE-2026-69192, CVE-2026-73566 | HIGH/CRITICAL | `node:24-alpine@sha256:e67514e5…` — `libssl3`, `tar`, and npm's bundled `brace-expansion`, `ip-address` | deferred | Same condition as the row above: fixes exist, the image has not been rebuilt, and `24-alpine` still resolves to this digest. Reduced impact worth naming: this is the **build stage only**. `frontend/Dockerfile` is multi-stage and the published `flagpole-web` image is `nginx-unprivileged` — no node, no npm and none of these packages ship in it. **Ends when** the tag resolves to a rebuilt digest. |
| 2026-09-02 | trivy | CVE-2025-69720, CVE-2026-11822, CVE-2026-11824, CVE-2026-13221, CVE-2026-16742, CVE-2026-41992, CVE-2026-42496, CVE-2026-42497, CVE-2026-48962, CVE-2026-54369, CVE-2026-57432, CVE-2026-57433, CVE-2026-8376, CVE-2026-9538 | HIGH | `python:3.12-slim@sha256:78387bc3…` — `perl-base`, `libsqlite3-0`, `ncurses-*`, `gzip`, `libacl1`, `libudev1` | accepted | Every one has `FixedVersion: none` — Debian has published no fix, so there is nothing to wait for and `deferred` would be dishonest. `flagpole-api` and `flagpole-consumer` run one uvicorn process as uid 10001 with a read-only root filesystem, no shell in the request path and no network ingress except through Traefik; `perl`, `gzip` and `ncurses` are never invoked. Re-check when Debian publishes fixes: the same scan will then move these to `deferred`. |
| 2026-09-02 | trivy | *(the base images were never scanned)* | — | `backend`, `consumer`, `frontend` base images | fixed | FR-010 names container images and `scripts/scan.sh` ran only `trivy fs` and `trivy config` — neither of which looks inside an image. 28 HIGH/CRITICAL findings in the three base images were invisible, and the contract file recorded trivy's coverage as "images and manifests". Found by the `code-reviewer` agent, not by the scanners. `scan.sh` now runs `trivy image` over every digest-pinned base named in the three Dockerfiles. |
| 2026-09-02 | osv-scanner | *(no package sources found)* | — | every lockfile | fixed | Pointed at a directory, osv-scanner walked the working tree — which locally includes `.venv` and `node_modules` and in CI does not, so the two runs could never agree (FR-013). Pointed at the copy of the tracked files instead, it honoured the `.gitignore` copied along with them and reported **no package sources found** while the summary still said clean. It now names its four lockfiles explicitly and refuses to run if one is missing. |
| 2026-09-02 | trivy | KSV-0046 | CRITICAL | `clusters/local/flux-system/gotk-components.yaml` — ClusterRoles `crd-controller-flux-system`, `flux-edit-flux-system`, `flux-view-flux-system` | accepted | Written by `flux bootstrap`, not by this repository. The controllers reconcile arbitrary Kubernetes objects from git, so a wildcard is what that job is; narrowing it would stop reconciliation. Changing it also loses the next `flux bootstrap`. The mitigation is elsewhere: only `flux-system` holds this, and the GitOps hook plus `permissions.deny` stop anything else writing to the cluster. |
| 2026-09-02 | trivy | KSV-0041 | CRITICAL | `clusters/local/flux-system/gotk-components.yaml` — ClusterRole `crd-controller-flux-system` | accepted | Same manifests, same reason: `kustomize-controller` decrypts SOPS Secrets and applies them, which is the feature this repository is built on. It cannot manage Secrets without permission to manage Secrets. |
| 2026-09-02 | trivy | KSV-0014 | HIGH | `deploy/base/postgres/statefulset.yaml` — container `postgres` | fixed | `readOnlyRootFilesystem` was `false` with a comment claiming PostgreSQL needs a writable root. It needs two directories, not a filesystem: `/var/run/postgresql` for the socket and lock file, and `/tmp`. Both are now `emptyDir`. Verified by running the same pinned image under `docker --read-only` with those two mounts: ready in 2s, `CREATE TABLE`/`INSERT` succeeded on the data volume, and `touch /usr/local/probe` was refused. |
| 2026-09-02 | gitleaks, trivy | `private-key` in `consumer/.keys/`, `mcp/flagpole-mcp/.keys/` | HIGH | the working tree | not applicable | Local development keys, generated by a script, gitignored, never committed — `git ls-files` returns nothing for either path and `gitleaks git .` finds nothing in 50 commits of history. The scanners were walking the developer's machine rather than the repository. `scripts/scan.sh` now scans a copy of the tracked files, which is scoping rather than suppression: nothing that is actually committed is excluded. |
| 2026-09-02 | bandit | B202, B324, B602 | HIGH | `mcp/flagpole-mcp/.venv/**` | not applicable | `bandit -r mcp/flagpole-mcp` descended into the virtualenv and reported pygments, cryptography, httpx and the MCP SDK as this repository's source. Fixed by naming the package (`mcp/flagpole-mcp/flagpole_mcp`) instead of the service directory. Dependencies are covered by pip-audit and osv-scanner, which is where a dependency finding belongs. |
| 2026-09-02 | trivy | *(none — the scanner had failed silently)* | — | `deploy`, `platform`, `clusters` | fixed | `trivy config` was invoked with three directories; it takes one and exits FATAL. The report was empty, `jq` returned nothing, and the summary said **clean**. This is exactly the FR-011 failure this feature exists to prevent, found by this feature's own first run. `scripts/scan.sh` now runs `trivy config` once per directory and treats output that does not parse as a failure rather than as silence. |
