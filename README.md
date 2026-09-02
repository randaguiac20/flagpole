# Flagpole

A small feature-flag service (FastAPI · React · k3d · Flux · SOPS/age · Renovate · Dex) whose real purpose is to teach **when, where and how far** to use each Claude Code extension mechanism, built through **Spec-Driven Development** with GitHub Spec Kit.

> Status: Phase 2 (Claude Code scaffolding + SDD bootstrap) complete. Features 001–006 follow, each on its own spec branch. See `docs/BLUEPRINT.md` for the exact steps so far.

## Quickstart (5 minutes, after Phase 4 lands)

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
| Subagents | `.claude/agents/*.md` | `docs/decisions/agent-*.md` | `docs/claude-code/agents.md` |
| Skills | `.claude/skills/*/SKILL.md` | `docs/decisions/skill-*.md` | `docs/claude-code/skills.md` |
| MCP | `.mcp.json`, `mcp/flagpole-mcp/` | `docs/decisions/mcp-*.md`, `cluster-status-mcp.md` | `docs/claude-code/mcp.md` |
| SDD (Spec Kit) | `.specify/`, `.claude/skills/speckit-*/`, `specs/` | `docs/decisions/spec-kit.md` | `docs/claude-code/sdd.md` |
| Plugin | `plugins/flagpole-tools/` (Phase 6) | — | `docs/claude-code/plugin.md` |

Cross-cutting: `docs/anti-patterns.md` (misuse per mechanism), `docs/gotchas.md` (where docs and prompt disagreed), `docs/walkthrough.md` (every component fired once, with output), `docs/ports.md`.

## Architecture

See `docs/architecture.md` (imported into `CLAUDE.md`).
