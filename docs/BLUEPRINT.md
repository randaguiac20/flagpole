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
