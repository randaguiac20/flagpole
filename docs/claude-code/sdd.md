# Spec-Driven Development with GitHub Spec Kit

Source: https://github.com/github/spec-kit (README, `docs/installation.md`) · release v1.0.3 (2026-09-01)

## What Spec Kit is, and how it extends Claude Code

Spec Kit is a CLI (`specify`) plus a set of prompts. `specify init --here --integration claude --script sh` writes:

- `.claude/skills/speckit-*/SKILL.md` — ten skills (`constitution`, `specify`, `clarify`, `plan`, `tasks`, `analyze`, `checklist`, `implement`, `converge`, `taskstoissues`), invoked as `/speckit-<name>` (hyphen; `invoke_separator` in `.specify/integration.json`). Each is an ordinary Claude Code skill: frontmatter + Markdown instructions that call the scripts below. **This is the lesson**: third-party tooling extends Claude Code with nothing but skills and shell scripts.
- `.specify/scripts/bash/` — `create-new-feature.sh` (numbers the feature, creates `specs/NNN-name/`, optionally the branch), `setup-plan.sh`, `setup-tasks.sh`, `check-prerequisites.sh`, `resolve-template.sh`, `common.sh`.
- `.specify/templates/` — spec, plan, tasks, checklist, constitution templates; `.specify/memory/constitution.md`; `.specify/workflows/` (a declarative full-cycle workflow); `.specify/.gitignore` (per-checkout `feature.json`).

Installed pinned: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@v1.0.3`; `specify version` / `specify check` to verify.

## The loop we use (per feature, on branch `NNN-name`)

1. `/speckit-constitution` — once. Wrote `.specify/memory/constitution.md` v1.0.0 (principles I–V, constraints, workflow, governance).
2. `/speckit-specify <description>` — user stories with priorities, Given/When/Then scenarios, FR-/SC- IDs, `[NEEDS CLARIFICATION]` markers.
3. `/speckit-clarify` — structured questions to the user; answers are written into the spec.
4. `/speckit-plan` — technical plan; its **Constitution Check** gate reads the constitution.
5. `/speckit-tasks` — ordered, testable tasks with file paths.
6. `/speckit-analyze` — cross-artifact consistency (spec ↔ plan ↔ tasks ↔ constitution). **Required before implement.**
7. `/speckit-implement` — executes tasks; then `code-reviewer` agent; then merge.
`/speckit-checklist` when acceptance criteria are fuzzy. `/speckit-converge` and `/speckit-taskstoissues` are installed but unused here (we finish features in one pass, and issues are not part of the demo).

## Constitution vs CLAUDE.md vs rules vs skills

| Holds | Where | Checked by |
|---|---|---|
| Principles and non-negotiables (test-first, no plaintext secrets, simplicity, GitOps) | `.specify/memory/constitution.md` | `/speckit-plan` gate, `/speckit-analyze` |
| Operational facts (commands, layout, names) | `CLAUDE.md` | every session |
| Language/directory conventions | `.claude/rules/` | when matching files are read |
| Procedures and reference | `.claude/skills/` | on demand |
None restates another; CLAUDE.md links to the constitution and `specs/`.

## Features and traceability

`001-flagpole-api`, `002-flagpole-web`, `003-flagpole-consumer`, `004-flagpole-mcp`, `005-platform-delivery`, `006-ci-and-security`. Code cites FR IDs in docstrings/comments, tests are named after scenarios (`SC-001 …`), decision records name the spec they serve. Claude Code scaffolding (Phase 2) is a chore: decision records, no spec.

## How to verify

`specify version` prints 1.0.3; `/speckit-constitution` appears in the `/` menu after a restart; `specs/NNN-*/` contains `spec.md`, `plan.md`, `tasks.md` and an `analyze` report section before any implementation commit.

## Common mistakes

Specs for chores; skipping `analyze`; editing the generated `speckit-*` skills (lost on refresh); a constitution listing build commands; letting the spec follow the code.
