# Memory: CLAUDE.md in every scope

Source: https://code.claude.com/docs/en/memory · https://code.claude.com/docs/en/features-overview

## What / where

| Scope | Location | In this repo | Purpose |
|---|---|---|---|
| Managed policy | Linux/WSL `/etc/claude-code/CLAUDE.md`; macOS `/Library/Application Support/ClaudeCode/CLAUDE.md`; Windows `C:\Program Files\ClaudeCode\CLAUDE.md`; or the `claudeMd` key in `managed-settings.json` | `claude-setup/managed/` + `install-managed.sh` | Org guidance every user gets; cannot be excluded with `claudeMdExcludes`. Enforcement still belongs in managed *settings*. |
| User | `~/.claude/CLAUDE.md`, `~/.claude/rules/` | `claude-setup/user/` + `install-user.sh` | Personal preferences, all projects |
| Project | `./CLAUDE.md` (or `./.claude/CLAUDE.md`) | `CLAUDE.md` | Team facts: commands, layout, conventions |
| Project rules | `./.claude/rules/*.md` | 4 files, see `rules.md` | Topic files, optionally path-scoped |
| Project local | `./CLAUDE.local.md` (gitignored) | `CLAUDE.local.md.example` | Personal per-checkout overrides |
| Auto memory | `~/.claude/projects/<project>/memory/` (`MEMORY.md` index + topic files) | not in repo | What Claude learns across sessions; `autoMemoryEnabled`, subagent `memory:` |

Load order: Managed → User → Project → Local; within a level `CLAUDE.md` then `CLAUDE.local.md`. Files from the working directory up to the root load at launch; a nested `CLAUDE.md` in a subdirectory loads on demand when Claude reads files there. The first 200 lines / 25 KB of `MEMORY.md` load every session.

## When / how far

Put in CLAUDE.md what every session needs and Claude got wrong twice: build/test commands, layout, names, "always/never" facts. Keep it under 200 lines (docs); this repo caps at 150 (currently 54). Reference material → skills; procedures → skills; path-specific conventions → rules; "every time X" → hooks; product principles → the SDD constitution (linked, not restated).

Imports: `@path` (relative to the importing file, or absolute, or `@~/...`), max depth 4 hops. An import that resolves outside the project triggers a one-time approval dialog. Block-level HTML comments are stripped before injection, so use them for maintainer notes.

## Our implementation

- `CLAUDE.md`: 54 lines, imports `@docs/architecture.md` (Mermaid + the three "environment" appearances), links to `.specify/memory/constitution.md` and `specs/`.
- `CLAUDE.local.md.example`: sandbox facts and the worktree caveat (a worktree does not see your `CLAUDE.local.md`; import a file outside the repo instead).
- `claude-setup/`: managed and user examples with installers that never run sudo.
- Auto memory: this project's memory holds the confirmed decisions (`flagpole-confirmed-decisions`), shown in the walkthrough.

## How to verify it loaded

- `/context`: lists every memory file with its token cost; `/memory`: opens them for editing; `/init` would generate a starter file (not used here, ours is hand-written); `/doctor` proposes trims when a checked-in CLAUDE.md is too large.
- `InstructionsLoaded` hook (see `hooks.md`, disabled by default): logs `session_start`, `nested_traversal`, `path_glob_match`, `include`, `compact` loads with the file path.
- After `/compact`: the project-root CLAUDE.md is re-read from disk; nested files and path-scoped rules re-load when matched again.
- `claudeMdExcludes` (any settings layer): glob patterns of absolute paths to skip, for monorepos with other teams' files.

## Common mistakes

Architecture essays; duplicating README/constitution; contradictory rules across scopes (Claude picks one arbitrarily); project facts in the user file; expecting a managed CLAUDE.md to *enforce* anything; forgetting that `CLAUDE.local.md` is invisible in worktrees.
