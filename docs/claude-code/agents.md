# Subagents: `.claude/agents/*.md`

Source: https://code.claude.com/docs/en/sub-agents

## What / where

A subagent is a Markdown file with YAML frontmatter and a system prompt. It runs in its own context window with its own tool list and returns a summary to the caller. Scopes (priority): managed > `--agents` CLI JSON > `.claude/agents/` (project) > `~/.claude/agents/` (user) > plugins. Built-ins: `Explore`, `Plan`, `general-purpose`, plus `fork` (inherits the parent conversation).

Frontmatter: `name`, `description` (when to delegate), `tools` / `disallowedTools` (comma-separated; `mcp__server__*`, `Agent(a, b)`), `model` (`sonnet|opus|haiku|fable|inherit|<id>`), `permissionMode`, `maxTurns`, `skills` (preloaded in full), `mcpServers`, `hooks` (scoped to the agent), `memory` (`user|project|local` → `.claude/agent-memory/<name>/`), `background`, `effort`, `isolation: worktree`, `color`.

## When / how far

Trigger: a side task reads many files or produces output you will not reference again; parallel independent tasks; a reviewer that must not edit; a restricted tool set. Not for ordinary sequential edits the user wants to watch. This repo: 4 agents — 2 in `.claude/`, 2 moved into the `flagpole-tools` plugin in Phase 6 alongside the skills that call them — explicit read-only `tools`, one-paragraph prompts.

Skill vs subagent: a skill is content loaded into *some* context (yours or a fork); a subagent is a worker with its own context. They combine: `skills:` preloads into an agent; `context: fork` runs a skill in a subagent. `SubagentStart`/`SubagentStop` hooks fire with `agent_type` = the agent's `name`.

## Our implementation

| Agent | Tools | Returns |
|---|---|---|
| `code-reviewer` | Read, Grep, Glob, `Bash(git diff/log/status *)` | verdict + findings table against rules and the spec |
| `security-auditor` | Read, Grep, Glob, scanner commands | triaged findings vs `docs/security-findings.md` |
| `deploy-verifier` | read-only kubectl/flux, `kubectl run` for in-cluster curl, `curl` | PASS/FAIL table |
| `ui-tester` | Read, Glob, `mcp__playwright__*`, `mcp__flagpole-mcp__*` | pass/fail per acceptance scenario + screenshots |

All: `model: inherit`, `maxTurns` 25–40, no `memory:` (reviewers must not drift from the spec), no write tools.

## How to verify

`/agents` lists project agents (created after session start → restart once). Spawn one: "Use the code-reviewer agent on the working tree". The transcript shows the delegation and the returned summary only.

## Common mistakes

Agents that duplicate the main session; omitting `tools` (inherits everything, including Edit); an agent per task; expecting an agent to see your conversation (only `fork` does); `memory:` on a reviewer; long system prompts that restate CLAUDE.md (it is loaded anyway).
