# BLUEPRINT — rebuild Flagpole from an empty folder

Exact commands and prompts, in order. Phases 3–6 are appended as they land. Prerequisites: Linux/macOS, Docker, `mise` (or the tools it installs), `uv`, Node 24, `gh` logged in, no sudo needed.

## Phase 0 — discovery (in Claude Code, plan mode)

1. Empty folder, `git init -b main`. Copy `PROMPT.md` in. Start `claude`, paste: `Ultrathink and read @PROMPT.md. Ask me any questions if needed`.
2. Claude checks the host, fetches the docs, and asks the `[CONFIRM]` rows in one message. Answers used here: all defaults; k3d instead of kind; Traefik instead of the retired ingress-nginx; cut `cluster-status-mcp`; public repo `randaguiac20/flagpole`.

## Phase 1 — plan

3. Approve the plan (`~/.claude/plans/…md`, copied into `docs/plan-phase1.md`).

## Phase 2 — Claude Code scaffolding + SDD bootstrap (chores, no spec)

```
mise use -g flux2@2.9.5 trivy@latest hadolint@latest osv-scanner@latest yq@latest
uv tool install pip-audit bandit semgrep ruff
uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.3
gh repo create randaguiac20/flagpole --public --source=. --remote=origin
specify init --here --force --non-interactive --integration claude --script sh
```
Then, with Claude: write `.gitignore`, `.env.example`, `scripts/ports.sh`, `CLAUDE.md` + `docs/architecture.md`, `CLAUDE.local.md.example`, `.claude/rules/` (4), `.claude/hooks/` (7 scripts + `lib.sh` + `tests/run.sh`), `Makefile`, `.claude/agents/` (4), `.claude/skills/` (5), `.mcp.json`, `claude-setup/`, `.claude/settings.local.json.example`, then `.claude/settings.json` last (hooks go live on save). Verify: `make test-hooks`; probe the guards (see `docs/walkthrough.md`). Constitution: `/speckit-constitution <principles>` (in a restarted session; in the authoring session the skill's steps were followed by hand, gotcha #6). Decision records + `docs/claude-code/*.md` + `docs/{gotchas,anti-patterns,ports}.md`. Commit on `main` with conventional commits.

Restart Claude Code, then run `/context`, `/hooks`, `/mcp`, `/agents`, `/memory` and paste into `docs/walkthrough.md`.
