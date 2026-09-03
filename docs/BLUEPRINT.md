# BLUEPRINT — rebuild Flagpole from an empty folder

Exact commands and prompts, in order. Phases 3–6 are appended as they land. Prerequisites: Linux/macOS, Docker, `mise` (or the tools it installs), `uv`, Node 24, `gh` logged in, no sudo needed.

## Phase 0 — discovery (in Claude Code, plan mode)

1. Empty folder, `git init -b main`. Copy `PROMPT.md` in. Start `claude`, paste: `Ultrathink and read @PROMPT.md. Ask me any questions if needed`.
2. Claude checks the host, fetches the docs, and asks the `[CONFIRM]` rows in one message. Answers used here: all defaults; k3d instead of kind; Traefik instead of the retired ingress-nginx; cut `cluster-status-mcp`; public repo `randaguiac20/flagpole`.

## Phase 1 — plan

3. Approve the plan (`~/.claude/plans/…md`, copied into `docs/plan-phase1.md`).

## Phase 2 — Claude Code scaffolding + SDD bootstrap (chores, no spec)

```
mise use -g flux2@2.9.5 trivy@latest hadolint@latest osv-scanner@latest yq@latest actionlint@latest
# renovate-config-validator is not installed: `npx --yes --package renovate -- renovate-config-validator`
uv tool install pip-audit bandit semgrep ruff
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.3
gh repo create randaguiac20/flagpole --public --source=. --remote=origin
specify init --here --force --non-interactive --integration claude --script sh
```
Then, with Claude: write `.gitignore`, `.env.example`, `scripts/ports.sh`, `CLAUDE.md` + `docs/architecture.md`, `CLAUDE.local.md.example`, `.claude/rules/` (4), `.claude/hooks/` (7 scripts + `lib.sh` + `tests/run.sh`), `Makefile`, `.claude/agents/` (4), `.claude/skills/` (5), `.mcp.json`, `claude-setup/`, `.claude/settings.local.json.example`, then `.claude/settings.json` last (hooks go live on save). Verify: `make test-hooks`; probe the guards (see `docs/walkthrough.md`). Constitution: `/speckit-constitution <principles>` (in a restarted session; in the authoring session the skill's steps were followed by hand, gotcha #6). Decision records + `docs/claude-code/*.md` + `docs/{gotchas,anti-patterns,ports}.md`. Commit on `main` with conventional commits.

Restart Claude Code, then run `/context`, `/hooks`, `/mcp`, `/agents`, `/memory` and paste into `docs/walkthrough.md`.

## Phase 3 — feature 001-flagpole-api (SDD loop, branch `001-flagpole-api`)

```
/speckit-specify 001-flagpole-api: <the section-4.1 description of flags, environments, evaluation, endpoints, roles, audit, seed, non-goals> Use the GIT_BRANCH_NAME 001-flagpole-api.
git switch -c 001-flagpole-api            # v1.0.3's script names the branch but does not create it
/speckit-clarify                          # answer the 4 questions (recommended answers were used)
/speckit-plan <technical context: Python 3.12/uv, FastAPI, SQLAlchemy 2 + Alembic, SQLite/PostgreSQL, PyJWT key resolver, instrumentator, layout>
/speckit-tasks
/speckit-analyze                          # apply findings spec-first, commit
/speckit-implement                        # tests first per story; `make test-fast` green
```
Then smoke-run uvicorn on 18000 (quickstart.md), run the `code-reviewer` agent on the branch, fix findings, merge to `main` (fast-forward).

## Phase 3 (continued) — feature 002-flagpole-web (SDD loop, branch `002-flagpole-web`)

```
/speckit-specify 002-flagpole-web: <sign-in, flag table per environment, operator vs viewer, audit view, non-goals> Use the GIT_BRANCH_NAME 002-flagpole-web.
git switch -c 002-flagpole-web
/speckit-clarify                          # 3 questions, batched into one prompt (gotcha #18)
/speckit-plan <technical context: Vite + React 19 + TypeScript, oidc-client-ts PKCE, types generated from the 001 contract, Vitest + Playwright>
/speckit-tasks
/speckit-analyze
/speckit-implement                        # Vitest first, then components
```
Then, before merging:

```
docker compose -f docker-compose.dev.yaml up -d dex   # started by scripts/dex-config.sh + playwright
make test                                             # hooks + backend + contract drift + frontend
make e2e                                              # Playwright starts Dex, the API and Vite itself
/e2e                                                  # the skill, once, to prove it works
ui-tester agent                                       # four scenarios in a real browser, screenshots
code-reviewer agent                                   # returned request-changes with 24 findings
```

Order matters here: the agents run **before** the merge, and the review is worth more than it looks —
it found a lint gate that compiled zero files and a type error hiding in the directory that gate never
covered. Fix findings spec-first (the contract change to the audit entry's `after` shape came before
the code), then merge to `main`.

Two things this phase adds that later phases depend on:

- `frontend/public/config.js` + `src/auth/config.ts` — the identity provider is read at run time, so
  feature 005 can ship one image into both namespaces.
- `dex/dev-config.yaml.tmpl` + `scripts/dex-config.sh` — Dex's ports come from `.env`, so nothing in
  the local stack hardcodes 18010.

## Phase 3 (continued) — feature 003-flagpole-consumer (SDD loop, branch `003-flagpole-consumer`)

```
/speckit-specify 003-flagpole-consumer: <one page, one endpoint; evaluates the seeded flag for a user; shows the decision it acted on; fail-safe to the plain page on any error, still HTTP 200; non-goals> Use the GIT_BRANCH_NAME 003-flagpole-consumer.
git switch -c 003-flagpole-consumer
/speckit-clarify
/speckit-plan <technical context: Python 3.12/uv, FastAPI + Jinja2, httpx with an explicit timeout, PyJWT service token, respx for every failure mode>
/speckit-tasks
/speckit-analyze
/speckit-implement
```

This is the phase that introduces a **second trusted issuer** in `backend/app/auth.py` — the consumer
authenticates as itself, not as a user. Amend the 001 spec first; the code follows the spec, never the
other way round.

## Phase 3 (continued) — feature 004-flagpole-mcp (SDD loop, branch `004-flagpole-mcp`)

```
/speckit-specify 004-flagpole-mcp: <three tools, one resource, one prompt over the flag service; every failure returns a kind and a message; non-goals> Use the GIT_BRANCH_NAME 004-flagpole-mcp.
git switch -c 004-flagpole-mcp
/speckit-clarify ; /speckit-plan ; /speckit-tasks ; /speckit-analyze ; /speckit-implement
cd mcp/flagpole-mcp && uv run pytest        # in-memory Client, no subprocess
```

Two things this phase teaches, both the hard way:

- The SDK is **`MCPServer`**, not `FastMCP` (renamed in the Python SDK 2.x) — gotcha #8.
- **Argument rules belong in the function signature.** They become the published input schema and the
  SDK enforces them before the body runs, so an in-body check is dead code that will silently disagree
  with the schema. `specs/004-flagpole-mcp/contracts/mcp-surface.json` is asserted against the running
  server's schema so the two cannot drift.

## Phase 4 — feature 005-platform-delivery (SDD loop, branch `005-platform-delivery`)

```
/speckit-specify 005-platform-delivery: <three images, a local cluster, GitOps, TLS, OIDC, network policy, one database per environment>
git switch -c 005-platform-delivery
/speckit-clarify ; /speckit-plan ; /speckit-tasks ; /speckit-analyze
scripts/verify-cluster.sh                 # written FIRST; fails against an empty cluster
/speckit-implement
make bootstrap && make cluster-up         # asks before it touches GitHub
make build && make deploy
scripts/verify-cluster.sh                 # 43 passed, 0 failed
```

Order that matters: the verification script is written before the manifests it verifies. Flux
**dry-runs a Kustomization's whole set before applying any of it**, so a controller and its custom
resources need separate units with `dependsOn` (gotcha #30) — that is why `clusters/local/` has both
`platform.yaml` and `platform-issuer.yaml`.

## Phase 5 — feature 006-ci-and-security (SDD loop, branch `006-ci-and-security`)

```
/speckit-specify 006-ci-and-security: <every change checked; dependencies proposed not chased; findings triaged not accumulated>
git switch -c 006-ci-and-security
/speckit-clarify                          # the version question: a VERSION file, changed by a person
/speckit-plan ; /speckit-tasks ; /speckit-analyze
scripts/check-ci-contract.sh              # written FIRST; 2 passed, 14 failed with no workflows
mise install                              # .mise.toml pins every check tool
make scan                                 # all eight scanners; the findings document is the gate
scripts/check-ci-contract.sh              # 100 passed, 0 failed
gh pr create --fill && gh pr checks --watch
```

Then, **before** merging, the `code-reviewer` agent. It returned request-changes with 15 findings,
five of them high, and three were the same shape: a check that reported clean when it had not run.
Fix them, prove each fix by breaking it, and only then merge. Merging fires `release.yml`, which
publishes three images tagged with `VERSION` and with the commit.

The user installs the Mend Renovate app on the repository once — a GitHub account action Claude
cannot take.

## Phase 6 — plugin, templates, reproduction (chores, no spec)

```
mkdir -p plugins/flagpole-tools/{.claude-plugin,skills,agents} .claude-plugin
git mv .claude/skills/{deploy-local,security-scan,e2e} plugins/flagpole-tools/skills/
git mv .claude/agents/{deploy-verifier,security-auditor}.md plugins/flagpole-tools/agents/
# write plugins/flagpole-tools/.claude-plugin/plugin.json and .claude-plugin/marketplace.json,
# then add extraKnownMarketplaces + enabledPlugins to .claude/settings.json
claude plugin marketplace add ./          # a bare `.` is rejected — gotcha #44
claude plugin install flagpole-tools@flagpole-local
claude plugin details flagpole-tools      # Skills (3), Agents (2), and the token cost
scripts/check-blueprint.sh                # this file, checked against the repository
```

Components were **moved, not copied**, and everything they own is now namespaced
(`/flagpole-tools:deploy-local`). Every hook stayed in `.claude/`: a plugin can be disabled with one
command, and a guard that can be switched off is not a guard.

`templates/` holds a de-Flagpoled copy of every mechanism plus a generic `PROMPT.md`. Nothing in it is
loaded by the running project — it is what you start the *next* repository from.

## Reproducing this file

`scripts/check-blueprint.sh` asserts this document against the repository: every tool it names is
installed, every path it says to create exists, and every `make` target it calls is defined. Run it
after editing either.

The one thing it cannot check is the part that needs an empty machine and a GitHub account — creating
the repository, `flux bootstrap`, and installing the Renovate app. Those are marked in the phases
above and are the user's to run.
