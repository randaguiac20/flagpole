# Flagpole — Claude Code Learning Demo (Prompt v3, Flux + SOPS/age + Renovate variant)

> **How to use:** paste as the first message in a fresh Claude Code session at the root of the empty repo. Confirm the **Decisions** table first (section 3). Rows marked `[CONFIRM]` must be asked about before any file is written.

Ultrathink every step. Use plan mode for Phases 0–1. Do not write files until the plan is approved.

---

## 1. Goal

I am learning Claude Code. The deliverable is a **small, professional, fully working demo app** whose real purpose is to teach me — by example and by documentation — **when, where, and how far** to use each Claude Code extension mechanism, using only **official, current** configuration, and to do it through **Spec-Driven Development (SDD)** so that specs, not chat, drive the code.

Four outcomes, in priority order:

1. **Judgment.** For every mechanism (memory scopes, rules, settings/permissions, skills, subagents, hooks, MCP, plugins) I must come away knowing: the problem it solves, the trigger that justifies adding it, the cheaper alternative it competes with, how far to take it, and the failure mode of overusing it.
2. **SDD discipline.** Every feature goes constitution → spec → clarify → plan → tasks → analyze → implement. I must see how a spec toolkit plugs into Claude Code and how it relates to CLAUDE.md, rules, and skills without duplicating them.
3. **A correct, reproducible reference implementation** of each mechanism, each justified by a real need in the demo — never added "because the feature exists."
4. **A working app** spanning frontend, backend, Python, Docker, Kubernetes, GitOps (Flux), CI automation, secrets (SOPS + age), dependency automation (Renovate), and authentication/authorization, running entirely in a local cluster.

Complexity budget goes to clarity and correct usage, not to app features. **Restraint is part of the lesson:** the docs must show what was deliberately *not* built and why.

---

## 2. Usage doctrine (apply this to every component you add)

Base this on the official page "Extend Claude Code" (`code.claude.com/docs/en/features-overview`) and the Anthropic blog post "Steering Claude Code" it links to. Fetch both. Then apply the rules below; where the docs and my rules differ, follow the docs and flag it in `docs/gotchas.md`.

### 2.1 The decision test (run it before creating any component)

1. **Can the built-in tools + a one-line CLAUDE.md instruction do this?** If yes, stop there.
2. **Is it always-on context or on-demand?** Always-on → CLAUDE.md or rule. On-demand → skill.
3. **Does it need to hold every time regardless of what Claude decides?** → hook (or `permissions.deny` if it is a plain allow/deny). An instruction is a request; a hook is enforcement.
4. **Does it need context isolation, parallelism, or would it flood the main conversation?** → subagent.
5. **Does Claude need data or actions from a system it cannot reach through the shell?** → MCP. If a CLI already exists (`kubectl`, `flux`, `gh`, `curl`), prefer Bash + a skill over a new MCP server.
6. **Will a second repo need the identical setup?** → plugin. Otherwise keep it in `.claude/`.
7. **Is this a feature (user-visible behavior) or a chore (tooling/config)?** Features go through SDD (section 2.5). Chores do not get a spec.

Record the answer for each component in a short decision record (see 2.3).

### 2.2 Per-mechanism rules: use / don't / how far

| Mechanism | Use it when | Do NOT use it for | How far (limits for this repo) | Overuse smell |
|---|---|---|---|---|
| **CLAUDE.md (project)** | Facts every session needs: build/test commands, layout, conventions, "always/never" rules. Trigger: Claude got it wrong twice. | Reference docs, procedures, anything derivable from the code, anything only relevant to a subtree, product principles (those live in the SDD constitution). | < 150 lines. Specific and verifiable. Points to the constitution and `specs/`; does not restate them. | Long prose, architecture essays, duplicated README/constitution content, contradictory rules. |
| **User / managed memory** | Personal preferences (user); org-wide policy that must not be excluded (managed). | Project-specific facts. | One short example each; ship as templates + installer. | Project rules leaking into user scope; managed file used for guidance that should be enforced via managed settings. |
| **Rules `.claude/rules/`** | Topic-specific conventions; path-scoped guidance that should load only when touching matching files. | Whole-project "always" rules; procedures. | 3–5 files. ≥ 2 path-scoped. One topic per file. | Many unconditional rules; overlapping globs. |
| **CLAUDE.local.md** | Personal per-project overrides (sandbox URLs, test data). | Anything a teammate needs. | Example file only; real file gitignored. Explain the worktree caveat and the `@~/...` import alternative. | Team conventions hidden in a local file. |
| **Settings / permissions** | Hard allow/deny/ask on tools and paths; hook registration; enabling plugins. | Behavioral guidance. | Allow list limited to the workflow; deny destructive git/kubectl/rm patterns; explain precedence. | `bypassPermissions` as a habit; allow lists that grant everything. |
| **Skills** | Repeatable multi-step procedures you'd otherwise paste, or reference material Claude needs sometimes. Trigger: pasted the same playbook 3 times. | Always-on rules; single-line commands; enforcement; re-implementing what Spec Kit already provides. | 3–5 skills of ours, plus the Spec Kit commands it installs. Precise `description`; `disable-model-invocation: true` on skills with side effects. | Skills that restate CLAUDE.md; vague overlapping descriptions; a skill per make target. |
| **Subagents** | Work that reads many files and returns a summary; parallel independent tasks; a reviewer that must not edit; a restricted tool set. | Ordinary sequential edits; anything the main session must see step by step. | 3–4 agents, each with explicit `tools` and a one-paragraph system prompt. Read-only for reviewers/auditors. | Agents that duplicate the main session; full tool access; agent per task. |
| **Hooks** | Things that must happen *every* time and need no reasoning: format after edit, block unsafe commands, log, notify, inject environment facts at session start. | Anything needing judgment; long-running work; substitutes for tests/CI; nagging. | See 2.4. ≤ 6 hooks; each justified by "a CLAUDE.md line was not sufficient because…". | Hooks calling the model; repo mutation on `PreToolUse`; looping `Stop` hooks; output flooding context. |
| **MCP servers** | External systems Claude can't reach via shell, or a browser (Playwright). Also to *learn* how to build one — state that honestly. | Wrapping a CLI that works from Bash; tool sprawl. | 1 official (Playwright) + ≤ 2 custom. stdio by default. Each tool must be used in the walkthrough. | Secrets in `.mcp.json`; HTTP servers binding ports for no reason. |
| **Plugins** | Reusing the same setup across repos or distributing it. | A single repo. | Optional Phase 6; same components moved, not new ones. | Plugin "for completeness". |
| **SDD (Spec Kit)** | Any user-visible feature or behavior change; anything with acceptance criteria. Trigger: you would otherwise explain requirements in chat. | Tooling chores (hooks, CI YAML, formatter config), one-line fixes. | One spec per feature, ≤ 6 features total, one feature branch each; `/speckit.analyze` before every `/speckit.implement`. | Specs for trivial changes; spec and code drifting apart; constitution duplicating CLAUDE.md. |

### 2.3 Decision records (mandatory)

For every component created, add `docs/decisions/<component>.md` (≤ 20 lines):

- Problem it solves in *this* repo (concrete trigger) and the spec ID it serves, if any.
- Alternative considered and rejected (e.g. "a CLAUDE.md line" / "a Bash command in a skill" / "no hook, rely on CI").
- Limits applied (scope, tools, matcher, `if`, timeout, size).
- What was deliberately **not** done, and the signal that would justify doing it later.
- Verification: the command/output proving it loaded and fired (`/context`, `/hooks`, `/mcp`, `/agents`, `InstructionsLoaded` log).

Also produce `docs/anti-patterns.md`: for each mechanism (including SDD), one short "how people misuse this" example, described, not implemented.

### 2.4 Hook hard rules (hooks are the sharpest tool — handle accordingly)

- Prefer `permissions.deny` for plain blocks; use a `PreToolUse` hook only when the rule needs to inspect content or arguments.
- Every hook: exec form (`command` + `args`), `${CLAUDE_PROJECT_DIR}` paths, narrow `matcher` + `if`, explicit `timeout` (≤ 10 s for tool events), deterministic, idempotent, no network, no LLM calls (`type: prompt/agent` hooks are documented but not enabled by default).
- Fail-open vs fail-closed is a written decision per hook. Enforcement hooks use exit 2 or `permissionDecision: deny`; never rely on exit 1.
- Hooks never mutate tracked files except formatters on `PostToolUse` for the touched file only.
- Hook stdout is context: return `additionalContext` only when Claude must act on it; log everything else to `.claude/logs/` (gitignored).
- A `Stop` hook may block at most once per turn (marker file) to avoid loops.
- Each hook has a shell test under `.claude/hooks/tests/` fed with sample stdin JSON, run by `make test-hooks`.
- Document exit-code semantics, JSON output fields, scopes, merge behavior, and `/hooks`.

### 2.5 Spec-Driven Development rules

Tool: **GitHub Spec Kit** (`github.com/github/spec-kit`, official, MIT). Read its README, installation guide, and the Claude Code integration notes before installing. Verify the current flag names (`--integration claude` in recent versions, `--ai claude` in older ones) and the current release tag; do not guess.

- Install pinned: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<latest-tag>`; then `specify init --here --integration claude --script sh`. Inspect what it wrote into `.claude/` (commands/skills) and `.specify/` and document it in `docs/claude-code/sdd.md` — this is the lesson on how third-party tooling extends Claude Code.
- Workflow per feature, on a branch named by Spec Kit (`001-…`): `/speckit.constitution` (once) → `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`. Use `/speckit.checklist` where acceptance criteria are fuzzy.
- **Constitution vs CLAUDE.md:** the constitution holds product and engineering principles and non-negotiables that the SDD gates check (testing policy, simplicity, security baseline, "no plaintext secrets"). CLAUDE.md holds operational facts (commands, layout, conventions) and links to the constitution. Neither restates the other.
- **Spec is the source of truth.** Code, tests, manifests, and decision records reference the spec ID. If implementation reveals the spec was wrong, update the spec first, then the code.
- Features (≤ 6): `001-flagpole-api`, `002-flagpole-web`, `003-flagpole-consumer`, `004-flagpole-mcp`, `005-platform-delivery` (containers, Kubernetes, Flux, secrets, auth), `006-ci-and-security`. Claude Code scaffolding (Phase 2) is a chore, not a feature — no spec.
- `[CONFIRM]` Fallback if Spec Kit is rejected: a lightweight `specs/<nnn>-<name>/{spec,plan,tasks}.md` with the same gates, driven by our own `/spec` skill.

---

## 3. Decisions — confirm or override before starting

Ask me to confirm every row in **one** message, then proceed. Never assume silently. Also ask: my OS (Linux / macOS / WSL / Windows) and whether you may run `sudo` for the managed-memory installer or should only print the command.

| Area | Default | Notes |
|---|---|---|
| **Demo app** | **Flagpole** — a feature-flag service (see section 4). | `[CONFIRM]` Alternatives in 4.3. |
| **SDD** | GitHub Spec Kit, pinned release, Claude integration | `[CONFIRM]` vs lightweight `specs/` fallback |
| Backend | Python 3.12, FastAPI, `uv`, SQLite (dev) / PostgreSQL (cluster), Alembic | `[CONFIRM]` DB |
| Frontend | `npm create vite@latest` React + TypeScript, Vitest, Playwright | `[CONFIRM]` |
| Custom MCP servers | Python, official `mcp` SDK (FastMCP), stdio. `flagpole-mcp` (list/evaluate/toggle flags, read audit log) and `cluster-status-mcp` (read-only: rollouts, Flux Kustomization/HelmRelease readiness). | `[CONFIRM]` — `cluster-status-mcp` is the one to cut if `kubectl`/`flux` in a skill is judged sufficient; decide and record it. |
| Playwright MCP | Official `@playwright/mcp` via `npx`, project scope in `.mcp.json` | |
| Containers | Multi-stage Dockerfiles, official images pinned by digest, non-root, `HEALTHCHECK` | |
| Kubernetes | `kind` local cluster, Kustomize base + `overlays/{dev,prod}` | `[CONFIRM]` kind vs k3d |
| GitOps | Flux (official `flux bootstrap github`), `clusters/local/` → `Kustomization`s `flagpole-dev`, `flagpole-prod`; platform components as `HelmRelease`s from official charts with pinned versions | `[CONFIRM]` (the Argo CD variant of this prompt is the alternative) |
| Secrets | SOPS + age: `.sops.yaml` creation rules, encrypted `Secret` manifests committed, Flux `decryption.provider: sops` with the age key in `flux-system` | `[CONFIRM]` vs Sealed Secrets |
| Dependency & image updates | Renovate (Mend GitHub App or `renovatebot/github-action`): Python (`uv.lock`), npm, Dockerfile digests, GitHub Actions, pre-commit, Flux `HelmRelease` chart versions, and image tags in `deploy/overlays` via the `kubernetes`/`flux` managers; PR-based | `[CONFIRM]` vs Flux image-reflector/automation controllers |
| CI | GitHub Actions: lint, test, scan, build/push to ghcr.io with semver tags Renovate can track | `[CONFIRM]` registry (`ghcr.io/<owner>`) |
| AuthN/AuthZ | Dex (OIDC, official Helm chart via `HelmRelease`) with static users; roles `viewer` / `operator`; backend validates JWT; frontend PKCE | `[CONFIRM]` vs Keycloak |
| Ingress / TLS | ingress-nginx + cert-manager self-signed | |
| Security scanning | `pip-audit`, `npm audit`, `osv-scanner`, `trivy` (image + IaC), `hadolint`, `gitleaks`, `bandit`, `semgrep` OSS | pre-commit + CI; hooks only for the fast ones |
| Plugin | Optional Phase 6 | `[CONFIRM]` include/skip |

---

## 4. The demo app

### 4.0 Naming (use these exactly)

| Thing | Name |
|---|---|
| Repo / project | `flagpole` |
| Backend service | `flagpole-api` (`backend/`) |
| Consumer service | `flagpole-consumer` (`consumer/`) |
| Frontend | `flagpole-web` (`frontend/`) |
| Custom MCP servers | `flagpole-mcp` (`mcp/flagpole-mcp/`), `cluster-status-mcp` (`mcp/cluster-status-mcp/`) if kept |
| Kubernetes namespace | `flagpole` |
| Container images | `ghcr.io/<owner>/flagpole-api`, `flagpole-consumer`, `flagpole-web` |
| Flux objects | `GitRepository/flagpole`, `Kustomization/platform`, `Kustomization/flagpole-dev`, `Kustomization/flagpole-prod`, `HelmRelease`s `ingress-nginx`, `cert-manager`, `dex` |
| Plugin (optional) | `flagpole-tools` |
| Spec IDs | `001-flagpole-api` … `006-ci-and-security` (section 2.5) |
| Seed flag used in the walkthrough | `new_banner` |

### 4.1 Flagpole, a feature-flag service

Concrete design — three concepts only: flags, environments, evaluation. This is the *intent*; the actual requirements are written and refined through `/speckit.specify` and `/speckit.clarify`, not copied from here.

- **Tables**: `flags` (`key`, `description`, `created_at`); `flag_environments` (`flag_key`, `env` ∈ {`dev`,`prod`}, `enabled`, `rollout_percent` 0–100); `audit_log` (`who`, `when`, `flag_key`, `env`, `before`, `after`).
- **Endpoints**: `GET /flags`, `POST /flags` (operator), `PUT /flags/{key}/env/{env}` (operator), `POST /evaluate` `{flag_key, env, user_id}` → `{enabled, reason}`, `GET /audit` (viewer+), `/healthz`, `/readyz`, `/metrics`. Nothing else.
- **Evaluation rule**: env disabled → `false`; else `sha256("{key}:{user_id}") % 100 < rollout_percent`. Deterministic so E2E never flakes.
- **Roles**: Dex JWT `groups` claim; `operators` → `operator`, everyone else → `viewer`. One FastAPI dependency enforces it.
- **Consumer**: one endpoint that evaluates `new_banner` for the logged-in user and renders a page with/without a banner.
- **Frontend**: login (PKCE), flag table with `dev`/`prod` tabs (toggle + rollout slider, disabled for viewers), audit log.
- **MCP `flagpole-mcp`**: tools `list_flags`, `evaluate_flag`, `toggle_flag`; resource `flags://{env}`; prompt `explain-rollout`. Used by the `ui-tester` agent to set state before driving the browser.
- **Overlays**: `dev`/`prod` differ in replicas, `ENV`, and a seed job creating the starter flags — the same "environment" idea in app, manifests, and Flux.
- **Tests**: `pytest` + `httpx`, MCP in-memory client tests, Vitest, Playwright E2E (driven by Claude via Playwright MCP during development *and* headless in CI).

Why this and not a network collector: deterministic (no live probes, no ICMP capabilities, no external targets), fully offline, natural RBAC, natural environments, a real service-to-service call to protect with NetworkPolicy, and MCP tools Claude actually uses during E2E.

### 4.2 Platform requirements

- **Containers**: per-service Dockerfile, `.dockerignore`, `hadolint` clean.
- **Kubernetes** `deploy/`: namespaces, Deployments, Services, Ingress, NetworkPolicies, resource requests/limits, PodSecurity `restricted`, least-privilege ServiceAccounts/RBAC, readiness/liveness probes, PDB where sensible. All services in-cluster.
- **GitOps (Flux)**: `flux bootstrap github` into `clusters/local/`; `platform` Kustomization (ingress-nginx, cert-manager, Dex as `HelmRelease`s with `HelmRepository` sources, pinned chart versions, `dependsOn` ordering) and app Kustomizations per env with `prune`, health checks, and `wait`. Docs explain source → kustomize/helm controllers, reconcile intervals, `flux reconcile`, suspend/resume, and rollback via git revert.
- **Secrets (SOPS + age)**: `age-keygen` in `make bootstrap` (key stored outside the repo, path in `.env.example`); `.sops.yaml` with `encrypted_regex: ^(data|stringData)$`; `sops --encrypt --in-place` workflow; age public key committed, private key created as `sops-age` secret in `flux-system`; Flux Kustomizations set `decryption.provider: sops`; `gitleaks` + a pre-commit check that every `kind: Secret` under `deploy/` carries `sops:` metadata; document key rotation and multi-recipient setup.
- **Renovate**: `renovate.json` extending `config:recommended`, with managers for `pep621`/`uv`, `npm`, `dockerfile` (digest pinning), `github-actions`, `pre-commit`, `flux` (HelmRelease chart versions), and `kubernetes`/`regex` for image tags in overlays; grouped PRs, semantic commits, a schedule; document how a Renovate PR merge becomes a Flux reconcile, and why Flux image automation was not chosen (or was, if you confirm it).
- **Automation**: `Makefile` targets `bootstrap`, `dev`, `test`, `test-hooks`, `scan`, `build`, `cluster-up`, `deploy`, `e2e`, `clean`; `pre-commit`; GitHub Actions workflows.

### 4.3 Alternatives (present these when asking for confirmation)

| Option | Strength | Weakness |
|---|---|---|
| Feature-flag service (default) | Deterministic, offline, natural roles/envs, real service-to-service, MCP tools with real use | Less "ops" flavor |
| Release board (what's deployed where, reading Flux + k8s) | Deep GitOps tie-in, read-only, safe | Needs a cluster even for local dev; little CRUD/authz; MCP would just wrap CLIs |
| Network collector, narrowed to HTTP/TCP health of in-cluster services | Closest to original idea, ops flavor | Timing-based results make E2E flaky; ICMP needs `NET_RAW`; external targets break offline demos |

---

## 5. Claude Code components to implement

Source of truth: `https://code.claude.com/docs/llms.txt` → fetch each relevant page. Do not rely on memory or third-party posts for file locations, frontmatter fields, hook events, or settings keys. Cite the doc page in each `docs/claude-code/*.md`.

### 5.1 Memory — all scopes

| Scope | Location | In repo? | Demo handling |
|---|---|---|---|
| Managed policy | Linux/WSL `/etc/claude-code/CLAUDE.md`; macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`; Windows `C:\Program Files\ClaudeCode\CLAUDE.md`; or `claudeMd` key in `managed-settings.json` | No | `claude-setup/managed/` example + `install-managed.sh` (asks before sudo). Explain: cannot be excluded; managed *settings* for enforcement, managed CLAUDE.md for guidance. |
| User | `~/.claude/CLAUDE.md`, `~/.claude/rules/` | No | `claude-setup/user/` example + `install-user.sh`. |
| Project | `./CLAUDE.md` (or `./.claude/CLAUDE.md`) | Yes | The real one. `@` imports for `docs/architecture.md`; links (not imports) to the constitution and `specs/`. |
| Project rules | `./.claude/rules/*.md` | Yes | 3–5 rules; ≥ 2 with `paths:` (`backend/**/*.py`, `frontend/**/*.{ts,tsx}`, `deploy/**/*.yaml`). |
| Project local | `./CLAUDE.local.md` | No (gitignored) | `CLAUDE.local.md.example`. |
| Auto memory | `~/.claude/projects/<project>/memory/` | No | Explain `MEMORY.md`, `/memory`, `autoMemoryEnabled`, subagent `memory:`; show one saved memory in the walkthrough. |

Also cover: nested `CLAUDE.md` load-on-demand, imports (max depth, external-import approval dialog), HTML comments stripped, load order, `/memory`, `/context`, `/init`, `/doctor` trim proposals, `claudeMdExcludes`, what survives `/compact`.

### 5.2 Settings and permissions

`.claude/settings.json` (committed): `permissions.allow/deny/ask`, hooks, `enabledPlugins`. `.claude/settings.local.json.example`. Explain precedence, permission modes, and the enforcement-vs-guidance table (settings vs CLAUDE.md vs hooks vs constitution).

### 5.3 Subagents — `.claude/agents/*.md`

- `code-reviewer` — read-only; reviews a diff against `.claude/rules/` **and the feature's spec**; returns findings only.
- `security-auditor` — runs scanners; read-only; returns a triaged report.
- `deploy-verifier` — after `/deploy-local`: checks rollouts, `flux get kustomizations` / `flux get helmreleases` all Ready, `/readyz` from inside the cluster; may use `cluster-status-mcp` if kept.
- `ui-tester` — Playwright MCP only; returns pass/fail with screenshots path, mapped to the spec's acceptance scenarios.

Each: `name`, `description`, `tools`, `model`, optional `memory`/`hooks`. Document skill-vs-subagent, `context: fork`, `skills:` preload, `SubagentStart/Stop`.

### 5.4 Skills — `.claude/skills/<name>/SKILL.md`

- `/deploy-local` — build, load into kind, `flux reconcile source git flagpole` + `flux reconcile kustomization flagpole-dev --with-source` and wait for Ready, then delegate to `deploy-verifier`. `disable-model-invocation: true`.
- `/security-scan` — full scanner run + triage template. `disable-model-invocation: true`.
- `/add-flag-field` — checklist: spec update → model → migration → API → MCP tool → UI → tests. Model-invocable.
- `/e2e` — run Playwright headless, attach report.
- One **reference** skill: `api-conventions` — the knowledge-not-workflow use.
- Do **not** re-create what Spec Kit installs; document its commands alongside ours and explain the naming boundary.

### 5.5 Hooks — `.claude/settings.json` + `.claude/hooks/*.sh` (≤ 6)

| Event | Matcher / `if` | Purpose | Why not CLAUDE.md |
|---|---|---|---|
| `SessionStart` (`startup\|resume`) | — | `additionalContext`: branch + active spec ID, kind status, Flux readiness of `flagpole-dev` and whether the age key is present, port table | Dynamic facts; must be fresh |
| `PreToolUse` | `Bash`, `if: "Bash(kubectl delete *)"` and `Bash(git push --force*)` | Deny | Must hold every time |
| `PreToolUse` | `Write\|Edit`, `if: "Edit(deploy/**)"` | Deny if a `kind: Secret` has `data:`/`stringData:` without `sops:` metadata (unencrypted secret) | Content inspection |
| `PostToolUse` | `Write\|Edit`, `if: "Edit(**/*.py)"` / `Edit(**/*.{ts,tsx})` | `ruff format` / `prettier` on the file | Guaranteed, needs no reasoning |
| `Stop` | — | Run fast unit tests; block once with reason | Guardrail on "done" |
| `Notification` (`permission_prompt`) | — | Desktop notify via `terminalSequence` | Side effect |

Plus one **documented-but-disabled** `InstructionsLoaded` logging hook, used once in the walkthrough to prove memory loading, then left off with the reason.

### 5.6 MCP servers

- `.mcp.json` (project scope, committed): `playwright`, `flagpole-mcp`, optionally `cluster-status-mcp`. `${ENV}` expansion; no secrets.
- Custom servers in `mcp/<name>/`: official `mcp` SDK, ≥ 2 tools, 1 resource, 1 prompt each, unit tests with the in-memory client, a `README` on stdio vs HTTP.
- **Ports**: stdio by default (no port). Anything that binds a port goes through `scripts/ports.sh` (checks `ss -ltn`/`lsof`, picks from the range in `.env.example`) and is listed in `docs/ports.md`. Never hardcode a port unchecked.
- Cover scopes and precedence, `claude mcp add/list/get`, `/mcp`, `claude mcp login`, `mcp__<server>__<tool>` naming in permissions/hooks, tool search.

### 5.7 Plugin (optional Phase 6)

`plugins/flagpole-tools/` with `.claude-plugin/plugin.json`, moving (not duplicating) the agents, skills, hooks, `.mcp.json`; local `marketplace.json`. Document namespacing and when a plugin is *not* warranted.

### 5.8 Reference-only (one paragraph each, no implementation)

`/init`, `/doctor`, `/context`, `/compact`, checkpointing/`/rewind`, permission modes and sandboxing, worktrees, headless `-p`, `claude-code-action` for GitHub, dynamic workflows, agent teams, the `security-guidance` plugin. Put in `docs/claude-code/reference.md`.

---

## 6. Process

1. **Phase 0 — Discovery (plan mode).** Fetch the Claude Code docs index and every relevant page; fetch the Spec Kit README and Claude integration notes; fetch the Flux, SOPS, age, Renovate, Dex docs you will rely on. Ask all `[CONFIRM]` questions in one message. Check host prerequisites (Docker, kind/k3d, kubectl, helm, `flux` CLI, `sops`, `age`/`age-keygen`, node, python, uv, jq); report gaps; never install system packages without asking.
2. **Phase 1 — Plan.** Directory tree; component list with doc page and decision-test answer for each; feature/spec list; port table; phase order. Wait for approval.
3. **Phase 2 — Claude Code scaffolding + SDD bootstrap (chores, no spec).** Memory, rules, settings, hooks, agents, skills, `.mcp.json`; `specify init`; `/speckit.constitution`. Verify with `/context`, `/hooks`, `/mcp`, `/agents`, `/memory`, and the `InstructionsLoaded` hook before any feature work. Write decision records as you go.
4. **Phase 3 — Features 001–004 via the SDD loop.** For each: specify → clarify (ask me) → plan → tasks → analyze → implement → `code-reviewer` → merge. Verify the UI through Playwright MCP after each meaningful change.
5. **Phase 4 — Feature 005 platform delivery via the SDD loop.** Docker → kind → `flux bootstrap` → age key + SOPS wiring → platform HelmReleases (ingress, cert-manager) → app Kustomizations → Dex. Prove: pods ready, all Flux Kustomizations and HelmReleases Ready with SOPS-decrypted secrets present, E2E green against the in-cluster app.
6. **Phase 5 — Feature 006 CI & security gate.** GitHub Actions pipeline producing Renovate-trackable image tags; `renovate.json` validated with `renovate-config-validator`; one Renovate PR shown end-to-end (open → merge → Flux reconcile). All scanners; fix or document every finding with severity and rationale. No open High/Critical.
7. **Phase 6 — Plugin (if confirmed), docs, and reproduction.** Run `docs/BLUEPRINT.md` from scratch in a temp dir and confirm it reproduces.

Working rules: conventional commits per task; one feature branch per spec; never commit secrets, `CLAUDE.local.md`, `settings.local.json`, or logs. Verify every claim by running it and showing output. Docs beat memory. If something cannot be done honestly, stop and present options. Fewer, clearer components beat exhaustive ones.

---

## 7. Sourcing rules

Allowed: `code.claude.com/docs`, `docs.claude.com`, `github.com/anthropics/*`, `github.com/modelcontextprotocol/*`, `github.com/microsoft/playwright-mcp`, `github.com/github/spec-kit`, official project docs (FastAPI, Vite, React, Playwright, Docker, Kubernetes, kind/k3d, Flux, SOPS, age, Renovate, Dex/Keycloak, cert-manager, ingress-nginx), official Docker images and Helm charts, upstream-maintained PyPI/npm packages.
Not allowed: "awesome" lists, blog snippets, unmaintained packages. Every dependency: maintained, pinned, scanned, listed with a one-line justification in `docs/dependencies.md`.

---

## 8. Deliverables checklist

- [ ] `README.md`: purpose, 5-minute quickstart, Mermaid architecture, and a map *mechanism → file → decision record → doc link*, plus *spec → code → tests* traceability.
- [ ] `docs/claude-code/<mechanism>.md` (memory, rules, settings, hooks, agents, skills, mcp, plugin, **sdd**): what / where / when / how far / our implementation / how to verify it loaded / common mistakes.
- [ ] `.specify/` + `specs/00N-*/` — constitution, and spec/plan/tasks per feature, all reconciled with the code.
- [ ] `docs/decisions/*.md` — one per component (section 2.3).
- [ ] `docs/anti-patterns.md` and `docs/gotchas.md`.
- [ ] `docs/BLUEPRINT.md` — rebuild from an empty folder, including the exact prompts and `/speckit.*` invocations per step.
- [ ] `templates/` — copy-ready `CLAUDE.md`, `CLAUDE.local.md.example`, `.claude/settings.json`, rule/agent/skill/hook templates, `.mcp.json`, managed/user examples, a constitution template, and `templates/PROMPT.md` (generic version of this prompt).
- [ ] `docs/walkthrough.md` — every hook, agent, skill, MCP tool, and `/speckit.*` command shown once with real output.
- [ ] `docs/ports.md`, `docs/dependencies.md`, `docs/security-findings.md`, `docs/secrets-sops.md` (key handling and rotation), `docs/renovate.md`.
- [ ] `make bootstrap && make cluster-up && make deploy && make e2e` green on a clean machine.

---

## 9. Mandatory constraints

- Do not omit, skip, or silently assume any item in sections 2, 4, 5, 8. If an item is impossible or unwise, say so and propose the alternative.
- Every component passes the decision test (2.1) and has a decision record (2.3). A component without a concrete trigger in this repo is not built — it is described in `docs/anti-patterns.md` instead.
- No feature code without a spec, plan, and tasks that passed `/speckit.analyze`.
- Simple, modular, pragmatic. The app is a vehicle; resist feature creep.
- All packages, images, and manifests pass the scanners; exceptions documented.
- No port collisions: check before binding.
- Batch questions; ask whenever a decision is not covered here.
