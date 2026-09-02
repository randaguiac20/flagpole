# Flagpole — Phase 1 plan (Claude Code learning demo, Flux + SOPS/age + Renovate)

## Context

PROMPT.md asks for a small, fully working feature-flag service ("Flagpole") whose real purpose is to teach when, where and how far to use each Claude Code extension mechanism, built through Spec-Driven Development with GitHub Spec Kit. Phase 0 (discovery) is done: host checked, official docs fetched (Claude Code docs index + memory/rules/settings/hooks/skills/subagents/mcp/plugins pages, "Extend Claude Code", the "Steering Claude Code" post, Spec Kit README + installation docs, Flux, SOPS, age, Renovate, k3d, Dex, cert-manager, Playwright MCP, MCP Python SDK). This file is the Phase 1 plan to approve before any file is written.

## Confirmed decisions (from the user)

| Area | Decision |
|---|---|
| App | Flagpole (flags / environments / evaluation) |
| SDD | Spec Kit **v1.0.3**, `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.3`, then `specify init --here --integration claude --script sh` |
| Backend | Python 3.12 (uv-managed), FastAPI, SQLAlchemy 2 + Alembic, SQLite (dev/tests), PostgreSQL in cluster (plain StatefulSet, official `postgres` image by digest, no operator) |
| Frontend | Vite + React + TypeScript, Vitest, Playwright |
| Custom MCP | `flagpole-mcp` only. `cluster-status-mcp` cut → decision record + anti-pattern entry |
| Cluster | **k3d** (installed, v5.9.0), bundled Traefik disabled so Flux owns ingress |
| GitOps | Flux v2.9.x, `flux bootstrap github --token-auth --personal --owner randaguiac20 --repository flagpole --branch main --path clusters/local` |
| Secrets | SOPS 3.13 + age 1.3, Flux `decryption.provider: sops`, `sops-age` secret in `flux-system` |
| Deps | Renovate via the **Mend GitHub App** (user installs it on the repo once); no token in repo |
| CI / registry | GitHub Actions → `ghcr.io/randaguiac20/{flagpole-api,flagpole-consumer,flagpole-web}` |
| Auth | Dex (chart `dex-0.24.1`, app 2.44), static users with `groups`, roles viewer/operator |
| Plugin | Phase 6 included (trigger = learning goal; recorded honestly) |
| GitHub repo | New **public** `randaguiac20/flagpole`, created with `gh`, local `main` pushed there |
| sudo | Never run by Claude. Installers print the command; user runs `! sudo …` |

## Deviations from PROMPT.md forced by the docs (go to `docs/gotchas.md`)

1. **ingress-nginx is retired** (repo archived 2026-03-24, no security fixes; upstream says "do not deploy it"). Replace with **Traefik** from the official chart (`https://traefik.github.io/charts`) as a Flux `HelmRelease`, keeping plain `Ingress` resources + cert-manager self-signed TLS so the rest of the prompt is unchanged. Flux object name becomes `HelmRelease/traefik`. (User to confirm; alternative = Envoy Gateway + Gateway API, larger change.)
2. **Hook `terminalSequence` does not exist.** The `Notification` hook uses `notify-send` (desktop) with a log fallback.
3. **MCP Python SDK is v2.1.1**: `FastMCP` was renamed `MCPServer` (`from mcp.server import MCPServer`); in-memory tests use `from mcp import Client`. Prompt text says FastMCP → documented.
4. **Spec Kit** installs `.claude/commands/speckit.*.md` (10 commands incl. new `/speckit.converge`, `/speckit.taskstoissues`). We use the 8 in the prompt as gates and document the other 2 as "not used, why".
5. **Plain blocks go to `permissions.deny`** (doctrine 2.4 wins over the 5.5 table): `Bash(git push --force*)`, `Bash(kubectl delete *)`, `Bash(rm -rf *)`. The `PreToolUse` Bash hook is kept for the case that *needs* argument inspection: a GitOps guard denying `kubectl apply|create|patch|edit|scale|rollout` against `flagpole-*` namespaces (Flux owns them) while allowing `flux-system`.
6. **Two envs in one cluster** → namespaces `flagpole-dev` and `flagpole-prod` (prompt names a single `flagpole`; both overlays cannot share one namespace). Ingress hosts `dev.flagpole.localhost`, `prod.flagpole.localhost`, `dex.flagpole.localhost` (systemd-resolved and Chromium resolve `*.localhost` to loopback; verified in Phase 4, `/etc/hosts` fallback printed, not written).
7. **Renovate key names**: `managerFilePatterns` (not `fileMatch`); `flux` and `kubernetes` managers need explicit patterns; `pre-commit` manager is off by default → enabled explicitly.
8. **CLAUDE.md**: docs say < 200 lines; we keep the stricter 150.

## Host prerequisites (no sudo needed for any)

Present: docker, kubectl 1.36, helm 4.2, k3d 5.9, sops, age, node 24, npm, uv, jq, gh (logged in, repo scope), git, pre-commit, gitleaks, kustomize, shellcheck, mise.
To install in Phase 2 via mise / uv tool (asking first, one batch): `mise use -g flux2@2.9.5 trivy hadolint osv-scanner yq`, `uv tool install pip-audit bandit semgrep`, `npx @playwright/mcp` (already configured at user scope). Python 3.12 pinned through uv (`.python-version`).

## Ports (dev, outside the cluster) — `docs/ports.md`, checked by `scripts/ports.sh`

| Service | Port | Note |
|---|---|---|
| flagpole-api (uvicorn) | 18000 | 8000 is taken on this host |
| flagpole-web (Vite) | 18010 | 5174/5175 taken |
| flagpole-consumer | 18020 | |
| Dex (docker compose, dev only) | 18030 | |
| PostgreSQL (docker compose, optional) | 18040 | |
| k3d loadbalancer | 80 / 443 | free on host |
| Range reserved | 18000–18099 | in `.env.example` |
MCP servers are stdio → no port.

## Repository layout

```
flagpole/
├── CLAUDE.md                     # <150 lines, @docs/architecture.md, links to constitution + specs/
├── CLAUDE.local.md.example
├── .claude/
│   ├── settings.json             # permissions allow/deny/ask, hooks, enabledPlugins (Phase 6)
│   ├── settings.local.json.example
│   ├── rules/                    # 4 rules: python-backend (paths), frontend (paths), k8s-manifests (paths), git-and-secrets (global)
│   ├── agents/                   # code-reviewer, security-auditor, deploy-verifier, ui-tester
│   ├── skills/                   # deploy-local, security-scan, add-flag-field, e2e, api-conventions
│   ├── commands/                 # written by Spec Kit (speckit.*.md) – not ours
│   ├── hooks/                    # session-start.sh, gitops-guard.sh, secret-guard.sh, format.sh, stop-tests.sh, notify.sh, instructions-loaded.sh (disabled) + tests/
│   └── logs/                     # gitignored
├── .mcp.json                     # playwright, flagpole-mcp
├── .specify/  specs/             # Spec Kit
├── backend/  consumer/  frontend/  mcp/flagpole-mcp/
├── deploy/base/  deploy/overlays/{dev,prod}/   # Kustomize; overlays set namespace, replicas, ENV, seed job
├── clusters/local/               # Flux: flux-system (bootstrap), platform/, apps/ (Kustomizations flagpole-dev, flagpole-prod)
├── platform/                     # HelmRepository + HelmRelease: traefik, cert-manager, dex; ClusterIssuer; postgres StatefulSet
├── .sops.yaml  renovate.json  .pre-commit-config.yaml  Makefile  .env.example
├── .github/workflows/            # ci.yml (lint/test/scan/build/push), e2e.yml
├── scripts/                      # ports.sh, bootstrap.sh, age-key.sh, check-sops-secrets.sh
├── claude-setup/{managed,user}/  # examples + install-managed.sh (prints sudo cmd) / install-user.sh
├── templates/                    # copy-ready versions of every mechanism + PROMPT.md generic
├── plugins/flagpole-tools/       # Phase 6
└── docs/  (architecture, claude-code/*, decisions/*, anti-patterns, gotchas, walkthrough, BLUEPRINT, ports, dependencies, security-findings, secrets-sops, renovate)
```

## Components and their decision-test answers (each gets `docs/decisions/<name>.md`)

| Component | Trigger in this repo | Cheaper alternative rejected | Limits | Doc page |
|---|---|---|---|---|
| CLAUDE.md | commands/layout/conventions every session needs | — | <150 lines, 1 import | memory |
| rules ×4 | Python, TS, k8s conventions only when touching those paths; secrets/git rule always | folding into CLAUDE.md (bloat) | 3 path-scoped + 1 global | memory#rules |
| CLAUDE.local.md.example | sandbox URLs / port overrides | — | example only | memory |
| managed/user examples | show scopes | — | templates + installers | memory |
| settings.json | deny destructive git/kubectl/rm, allow workflow cmds, hook registration | CLAUDE.md "never" (a request, not enforcement) | narrow allow list | settings, permissions |
| hook SessionStart | branch/spec/cluster/Flux/age-key facts change per session | static CLAUDE.md line (stale) | startup\|resume, 10 s, additionalContext only | hooks |
| hook PreToolUse Bash (gitops-guard) | must inspect kubectl args + namespace | permissions.deny cannot express "except flux-system" | `if: Bash(kubectl *)`, 5 s, fail-closed | hooks |
| hook PreToolUse Write\|Edit (secret-guard) | needs file content: `kind: Secret` with data but no `sops:` | deny rule cannot read content | `if: Edit(deploy/**)`+`Write(deploy/**)`, 5 s, fail-closed | hooks |
| hook PostToolUse (format) | ruff/prettier on touched file every time | CLAUDE.md "run ruff" (forgotten) | touched file only, 10 s, fail-open | hooks |
| hook Stop (fast tests) | guardrail on "done" | CI (too late for the session) | marker file, blocks once, 10 s | hooks |
| hook Notification | desktop notify on permission_prompt | none | notify-send, fail-open | hooks |
| hook InstructionsLoaded (disabled) | prove memory loading once | — | documented, off | hooks |
| agent code-reviewer | review diff vs rules + spec, must not edit | main session review (floods context) | Read/Grep/Glob/Bash(git diff*) | sub-agents |
| agent security-auditor | scanners produce huge output | main session | Read/Bash(scanners) | sub-agents |
| agent deploy-verifier | kubectl/flux checks after deploy | inline in skill | Read/Bash(kubectl get*, flux get*, curl*) | sub-agents |
| agent ui-tester | drives Playwright MCP, returns pass/fail | main session (screens flood) | mcp__playwright__* + Read | sub-agents |
| skill deploy-local | multi-step build→import→reconcile procedure pasted repeatedly | Makefile target alone (no verify delegation) | disable-model-invocation | skills |
| skill security-scan | full scan + triage template | `make scan` alone | disable-model-invocation | skills |
| skill add-flag-field | cross-cutting checklist spec→model→migration→API→MCP→UI→tests | CLAUDE.md (too long) | model-invocable | skills |
| skill e2e | run Playwright headless + report | Makefile target | model-invocable | skills |
| skill api-conventions | reference knowledge loaded on demand | CLAUDE.md (bloat) | reference only | skills |
| MCP playwright | browser Claude cannot drive from shell | — | project `.mcp.json`, headless flag | mcp |
| MCP flagpole-mcp | ui-tester sets flag state before browsing; learning to build one | curl in a skill (honest: would suffice) | stdio, 3 tools/1 resource/1 prompt | mcp |
| cluster-status-mcp | **not built** | kubectl/flux in Bash | — | anti-patterns |
| plugin flagpole-tools | Phase 6, learning goal | keep in `.claude/` | moved, not duplicated | plugins |
| Spec Kit | every user-visible feature | chat requirements | 6 specs, analyze before implement | sdd |

## Features (SDD, one branch each)

`001-flagpole-api` → `002-flagpole-web` → `003-flagpole-consumer` → `004-flagpole-mcp` → `005-platform-delivery` → `006-ci-and-security`. Constitution written once in Phase 2 (`/speckit.constitution`). Per feature: specify → clarify (questions to user) → plan → tasks → analyze → implement → code-reviewer → merge to main.

## Phase order and verification

- **Phase 2 – scaffolding (chores, no spec):** `gh repo create randaguiac20/flagpole --public`, initial commit; install missing tools (ask first); memory/rules/settings/hooks/agents/skills/.mcp.json; `specify init --here --integration claude --script sh`; `/speckit.constitution`; hook tests (`make test-hooks`); verify with `/context`, `/hooks`, `/mcp`, `/agents`, `/memory`, InstructionsLoaded hook once. Decision records written as each component lands.
- **Phase 3 – features 001–004:** SDD loop; pytest+httpx, Vitest, MCP in-memory `Client` tests; Playwright MCP checks after UI changes; dev auth via Dex in docker compose.
- **Phase 4 – feature 005:** Dockerfiles (digest-pinned, non-root, HEALTHCHECK, hadolint) → k3d cluster (`--k3s-arg "--disable=traefik@server:*"`, `-p 80:80@loadbalancer -p 443:443@loadbalancer`) → `flux bootstrap github` → age key + `.sops.yaml` + `sops-age` secret → platform HelmReleases (traefik, cert-manager, dex, `dependsOn`) → app Kustomizations (prune, wait, healthChecks) → PostgreSQL + SOPS secrets → NetworkPolicy, PSS restricted, RBAC, PDB. Proof: `flux get kustomizations/helmreleases` all Ready, `kubectl get secrets` decrypted, E2E green in-cluster.
- **Phase 5 – feature 006:** GitHub Actions (lint/test/scan/build/push semver tags), `renovate.json` validated with `renovate-config-validator`, Mend app installed by user → one Renovate PR merged → Flux reconcile shown; all scanners clean or documented in `docs/security-findings.md`.
- **Phase 6:** plugin move, docs (walkthrough with real output, BLUEPRINT, templates), BLUEPRINT re-run in a temp dir.

Final gate: `make bootstrap && make cluster-up && make deploy && make e2e` green.

## Deliberately not built (→ `docs/anti-patterns.md`)

cluster-status-mcp; prompt/agent-type hooks; Flux image automation (Renovate covers it); Keycloak; an operator for PostgreSQL; HTTP MCP transports; more than 4 agents; a skill per make target; Gateway API migration (documented as the future signal).
