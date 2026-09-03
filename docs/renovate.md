# Renovate

Feature 005 pinned everything this repository depends on. This is the mechanism that keeps a pin
from becoming a museum piece. Configuration: [`renovate.json`](../renovate.json). Decision record:
[`docs/decisions/dependency-updates-renovate.md`](decisions/dependency-updates-renovate.md).

## How it is delivered

The **Mend-hosted GitHub App**, installed once on `randaguiac20/flagpole` by its owner:

> <https://github.com/apps/renovate> → Configure → randaguiac20 → select `flagpole`

Nothing in this repository holds a token for it, and there is no scheduled workflow running Renovate
itself. That is the whole reason the hosted app was chosen over self-hosting: a self-hosted updater
means a credential with write access running unattended.

## What it updates

| Manager | Files | Note |
|---|---|---|
| `pep621` | `backend/`, `consumer/`, `mcp/flagpole-mcp/` `pyproject.toml` | uv lockfiles updated alongside |
| `npm` | `frontend/package.json` | lockfile updated alongside |
| `dockerfile` | the three `Dockerfile`s | `pinDigests` keeps `@sha256:…` a digest |
| `github-actions` | `.github/workflows/*.yml` | SHA pins; the tag comment moves with them |
| `pre-commit` | `.pre-commit-config.yaml` | **off by default** — enabled explicitly |
| `mise` | `.mise.toml` | the scanner and lint tool versions |
| `flux` | `platform/`, `clusters/` | chart and controller versions |
| `helm-values` | `platform/*/release.yaml` | images named inside chart values |
| `kubernetes` | `deploy/**` | the image tags Flux applies |

Two of those — `pre-commit` and `kubernetes` — are off unless a configuration turns them on, and
`kubernetes` additionally needs explicit patterns because there is no filename convention it can
infer. A manager that is off silently is a set of pins nobody is watching, which is worse than not
pinning: it looks maintained.

## How proposals are shaped

- **Non-major updates are grouped** into four changes — language packages, container images,
  tooling, platform charts — in one window a week (`before 6am on monday`), at most three open at a
  time. Thirty separate proposals is the same as none, because nobody reads thirty.
- **Majors arrive alone and unscheduled.** A major is a decision, not a bump.
- **Nothing merges itself.** `automerge: false`, everywhere, checked by
  `scripts/check-ci-contract.sh`.

## What Renovate does *not* touch

- **The images this repository publishes** (`ghcr.io/randaguiac20/flagpole-*`). They move because
  `VERSION` moved and `release.yml` published them — not because an updater proposed a bump to
  something this repository builds itself.
- **The cluster.** Renovate opens a change; a person merges it; Flux reconciles. That chain is the
  point, and it is why Flux's own image automation is deliberately not enabled — see
  `docs/anti-patterns.md`.

## The trap

The configuration key is **`managerFilePatterns`**. It was called `fileMatch` before Renovate 41,
and half the examples online still use the old name. `renovate-config-validator` does **not** refuse
it: it prints `WARN: Config migration necessary`, shows the migration diff, and **exits 0**. A
workflow step that only reads the exit status will let a deprecated key through. So the lint job
greps the validator's output, and `scripts/check-ci-contract.sh` asserts the key is absent.

## Checking it before it runs

```bash
npx --yes --package renovate -- renovate-config-validator renovate.json
scripts/check-ci-contract.sh
```
