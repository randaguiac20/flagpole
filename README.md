# Flagpole

A small feature-flag service (FastAPI · React · k3d · Flux · SOPS/age · Renovate · Dex) whose real purpose is to teach **when, where and how far** to use each Claude Code extension mechanism, built through **Spec-Driven Development** with GitHub Spec Kit.

> **New here? Start with [`docs/TUTORIAL.md`](docs/TUTORIAL.md)** — thirteen lessons that take this
> repository apart in the order the concepts build, from `make bootstrap` to a running cluster.
> Everything else below is reference.

> Status: all six features (001–006) are done. `docs/BLUEPRINT.md` has the exact steps, and
> `docs/walkthrough.md` the real output of each one.

## Run it locally

```
make dev     # Dex :18030, API :18000, web :18010 — sign in as alice@flagpole.local / flagpole
make test    # hook tests, backend tests, contract drift check, frontend tests
make e2e     # Playwright; starts everything it needs itself
```

Demo users are static and local only: `alice` has the operator role, `bob` the viewer role.

## Quickstart (the whole stack)

```
make bootstrap && make cluster-up && make deploy && make e2e
```

## Map: mechanism → file → decision → doc

| Mechanism | File(s) | Decision record | Doc |
|---|---|---|---|
| Project memory | `CLAUDE.md` (+ `@docs/architecture.md`), `CLAUDE.local.md.example` | `docs/decisions/claude-md.md`, `claude-local-md.md` | `docs/claude-code/memory.md` |
| Managed / user memory | `claude-setup/` | `docs/decisions/managed-and-user-memory.md` | `docs/claude-code/memory.md` |
| Rules | `.claude/rules/*.md` | `docs/decisions/rules.md` | `docs/claude-code/rules.md` |
| Settings / permissions | `.claude/settings.json`, `settings.local.json.example` | `docs/decisions/settings-permissions.md` | `docs/claude-code/settings.md` |
| Hooks | `.claude/hooks/*.sh`, `.claude/hooks/tests/` | `docs/decisions/hook-*.md` | `docs/claude-code/hooks.md` |
| Subagents | `.claude/agents/*.md`, `plugins/flagpole-tools/agents/*.md` | `docs/decisions/agent-*.md` | `docs/claude-code/agents.md` |
| Skills | `.claude/skills/*/SKILL.md`, `plugins/flagpole-tools/skills/*/SKILL.md` | `docs/decisions/skill-*.md` | `docs/claude-code/skills.md` |
| MCP | `.mcp.json`, `mcp/flagpole-mcp/` | `docs/decisions/mcp-*.md`, `cluster-status-mcp.md` | `docs/claude-code/mcp.md` |
| SDD (Spec Kit) | `.specify/`, `.claude/skills/speckit-*/`, `specs/` | `docs/decisions/spec-kit.md` | `docs/claude-code/sdd.md` |
| Plugin + marketplace | `plugins/flagpole-tools/`, `.claude-plugin/marketplace.json` | `docs/decisions/plugin-flagpole-tools.md` | `docs/claude-code/plugins.md` |
| CI, updates, scanning | `.github/workflows/`, `renovate.json`, `.mise.toml`, `scripts/scan.sh` | `docs/decisions/ci-github-actions.md`, `dependency-updates-renovate.md`, `versioning.md`, `security-scanning.md` | `docs/renovate.md`, `docs/security-findings.md` |
| **Tutorial** | `docs/TUTORIAL.md` — the guided course | — | asserted by `scripts/check-tutorial.sh` |
| Templates | `templates/` — every mechanism, de-Flagpoled, plus a generic `PROMPT.md` | — | `templates/README.md` |

Cross-cutting: `docs/anti-patterns.md` (misuse per mechanism, and what was deliberately not built), `docs/gotchas.md` (52 rows where the docs, the prompt or my own assumption disagreed with what actually happened), `docs/walkthrough.md` (every component fired once, with real output), `docs/BLUEPRINT.md` (rebuild from an empty folder, asserted by `scripts/check-blueprint.sh`), `docs/ports.md`.

## Architecture

See `docs/architecture.md` (imported into `CLAUDE.md`).
