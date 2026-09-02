# Rules: `.claude/rules/*.md`

Source: https://code.claude.com/docs/en/memory#organize-rules-with-claude/rules/

## What / where

Markdown files under `.claude/rules/` (recursive; symlinks allowed). A rule without frontmatter loads at launch with the same priority as `.claude/CLAUDE.md`. A rule with `paths:` frontmatter loads only when Claude reads a file matching one of the globs (gitignore-style: `**`, `*`, brace expansion `*.{ts,tsx}`, budget of 1,000 expanded patterns per rule). User-level rules live in `~/.claude/rules/` and load before project rules, so project rules win.

## When / how far

Trigger: CLAUDE.md is growing with conventions that only matter for one language or directory. One topic per file, a descriptive filename, no overlapping globs. This repo: 3–5 files, at least 2 path-scoped.

Not for: whole-project "always" rules (CLAUDE.md), procedures (skills), enforcement (hooks/permissions: a rule is still a request).

## Our implementation

| File | `paths` | Why it exists |
|---|---|---|
| `python-services.md` | `backend/**/*.py`, `consumer/**/*.py`, `mcp/**/*.py` | shared FastAPI/pytest/ruff conventions for three services |
| `frontend.md` | `frontend/**/*.ts`, `frontend/**/*.tsx` | React/TS, PKCE tokens in memory, `data-testid` |
| `kubernetes-manifests.md` | `deploy/**/*.yaml`, `clusters/**/*.yaml` | Flux owns the cluster, SOPS, PSS restricted, labels, overlay limits |
| `workflow.md` | (always) | spec-first, branches, commits, never-commit list, ports, ask-before |

## How to verify

Read a `.py` file, then run `/context`: `python-services.md` appears; it did not before. With the `InstructionsLoaded` hook enabled locally, `.claude/logs/instructions-loaded.log` shows `path_glob_match ... globs=[...]`.

## Common mistakes

Many unconditional rules (same cost as a big CLAUDE.md); overlapping globs with contradictory advice; putting a 30-step procedure in a rule (it is a skill); using a rule as a guardrail ("never edit .env": that is a `Read`/`Edit` deny rule).
