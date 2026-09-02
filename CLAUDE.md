# Flagpole

Feature-flag service built as a **Claude Code + Spec-Driven Development learning demo**. The app is the vehicle; the lesson is *which* Claude Code mechanism to use, *when*, and *how far*. Restraint is part of the lesson.

@docs/architecture.md

## Where things are

| Path | What |
|---|---|
| `backend/` `consumer/` `frontend/` `mcp/flagpole-mcp/` | The four codebases (Python/uv, Python/uv, Vite+React+TS, Python MCP server) |
| `specs/NNN-*/` | Spec Kit artifacts per feature: `spec.md`, `plan.md`, `tasks.md`. **Source of truth for behavior.** |
| `.specify/memory/constitution.md` | Product & engineering principles the SDD gates check. Not restated here. |
| `deploy/` | Kustomize `base/`, `overlays/{dev,prod}/`, `platform/` (Traefik, cert-manager, Dex, PostgreSQL). SOPS-encrypted Secrets. |
| `clusters/local/` | Flux entry points: `flux-system/`, `platform.yaml`, `flagpole-dev.yaml`, `flagpole-prod.yaml` |
| `.claude/` | rules, agents, skills, hooks, settings — each explained in `docs/claude-code/` and justified in `docs/decisions/` |
| `docs/` | `walkthrough.md`, `gotchas.md`, `anti-patterns.md`, `ports.md`, `secrets-sops.md`, `renovate.md`, `BLUEPRINT.md` |

## Commands

```
make bootstrap      # tools check, uv sync, npm ci, age key (outside repo), pre-commit install
make dev            # api :18000, web :18010, consumer :18020, dex :18030 (ports from .env.example)
make test           # all unit tests;  make test-fast = the subset the Stop hook runs
make test-hooks     # shell tests for every hook in .claude/hooks/tests
make scan           # pip-audit, npm audit, osv-scanner, trivy, hadolint, gitleaks, bandit, semgrep
make build          # docker images, digest-pinned bases
make cluster-up     # k3d cluster + flux bootstrap github (asks first)
make deploy         # import images, flux reconcile, wait for Ready
make e2e            # Playwright headless against the cluster
```

Per service: `cd backend && uv run pytest`, `cd frontend && npm test`, `cd mcp/flagpole-mcp && uv run pytest`.

## Conventions that must hold

- Behavior comes from `specs/`. No feature code without spec → plan → tasks → `/speckit-analyze`. Chores (hooks, CI, docs) need no spec.
- Feature branches are named by Spec Kit (`001-flagpole-api`). Conventional commits; spec ID in the body.
- Flux owns the cluster: edit manifests, never `kubectl apply` into `flagpole-*` namespaces (hook-enforced).
- Secrets: only SOPS-encrypted `kind: Secret` files are committed (hook-enforced). The age private key lives in `~/.config/sops/age/`, never in the repo.
- Ports come from `scripts/ports.sh`; the project range is 18000–18099. Cluster ingress is on 80/443 via k3d.
- Verify every claim by running the command and showing the output.

## Names (use exactly)

Services `flagpole-api`, `flagpole-consumer`, `flagpole-web`; MCP `flagpole-mcp`; images `ghcr.io/randaguiac20/<service>`; namespaces `flagpole-dev`, `flagpole-prod`; Flux `GitRepository/flagpole`, `Kustomization/platform|flagpole-dev|flagpole-prod`, `HelmRelease/traefik|cert-manager|dex`; seed flag `new_banner`; hosts `dev.flagpole.localhost`, `prod.flagpole.localhost`, `dex.flagpole.localhost`.

## Claude Code map (details in docs/claude-code/)

- Always-on: this file + `.claude/rules/workflow.md`. Path-scoped rules load for Python, frontend and manifests.
- On demand: skills `/deploy-local`, `/security-scan`, `/e2e`, `/add-flag-field`, `api-conventions`; Spec Kit's `/speckit-*`.
- Isolated: agents `code-reviewer`, `security-auditor`, `deploy-verifier`, `ui-tester`.
- Enforced: `permissions.deny` for plain blocks; hooks for content-dependent guards, formatting, the Stop test gate and notifications.
- External: MCP `playwright` (browser) and `flagpole-mcp` (flag state) in `.mcp.json`.
