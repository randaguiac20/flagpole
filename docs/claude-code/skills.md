# Skills: `.claude/skills/<name>/SKILL.md`

Source: https://code.claude.com/docs/en/skills

## What / where

A skill is a directory with `SKILL.md` (frontmatter + Markdown) and optional supporting files. Locations: `.claude/skills/` (project), `~/.claude/skills/` (user), plugins (namespaced `/plugin:skill`), managed. Legacy `.claude/commands/*.md` still work. Precedence for the same name: managed > user > project. Descriptions of model-invocable skills are in context every request (≤ 1,536 chars each); the body loads when invoked with `/name` or when Claude matches the description.

Frontmatter we use: `name`, `description`, `argument-hint`, `disable-model-invocation` (user-only: invisible to Claude until you type it), `user-invocable: false` (Claude-only background knowledge), `allowed-tools` (pre-approved for the invoking turn). Also available: `context: fork` + `agent`, `paths` (auto-activate only for matching files), `hooks`, `model`, `effort`, `arguments`. Substitutions: `$ARGUMENTS`, `$0`/`$1`, `${CLAUDE_PROJECT_DIR}`, `${CLAUDE_SKILL_DIR}`; `` !`command` `` runs at load time and injects the output.

## When / how far

Trigger: you keep typing the same prompt, or pasted the same playbook three times, or Claude needs reference material sometimes. Not for always-on rules, single commands, enforcement, or re-implementing what Spec Kit provides. This repo: 5 of ours + 10 from Spec Kit. `disable-model-invocation: true` on skills with side effects.

## Our implementation

| Skill | Kind | Invocation | Tools pre-approved |
|---|---|---|---|
| `/deploy-local` | procedure with side effects | user only | make, scripts, k3d, flux, kubectl get, `Agent(deploy-verifier)` |
| `/security-scan` | procedure + fixed triage template | user only | make scan, `Agent(security-auditor)` |
| `/add-flag-field` | checklist | user or Claude | none needed |
| `/e2e` | procedure | user or Claude | make e2e, ports, Read |
| `api-conventions` | reference | Claude only (`user-invocable: false`) | — |

Naming boundary with Spec Kit: Spec Kit owns the `speckit-` prefix (`/speckit-constitution` … `/speckit-taskstoissues`), installed by `specify init` and refreshed by it; we never edit those files. Our skills never start with `speckit-`.

## How to verify

`/` menu shows user-invocable skills; `/context` lists loaded skill descriptions; invoking `/deploy-local` shows the injected `k3d cluster list` preflight. New top-level `.claude/skills/` directories need a restart (gotcha #6).

## Common mistakes

Skills that restate CLAUDE.md; vague overlapping descriptions ("helps with deployment"); a skill per make target; side-effect skills left model-invocable; putting 200 lines of reference in `description` instead of the body.
