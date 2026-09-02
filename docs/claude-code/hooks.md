# Hooks

Source: https://code.claude.com/docs/en/hooks (reference) · https://code.claude.com/docs/en/hooks-guide

## What / where

Hooks run *your* command (or HTTP request, MCP tool, prompt, agent) at a lifecycle event, deterministically, outside the model. Registered under `hooks` in any settings file, in a plugin's `hooks/hooks.json`, or in skill/agent frontmatter; hooks from every source merge and all matching hooks run in parallel. Scripts live in `.claude/hooks/` and are referenced as `${CLAUDE_PROJECT_DIR}/.claude/hooks/x.sh` in **exec form** (`command` + `args`: no shell, no quoting surprises).

Events we use: `SessionStart` (matcher = `startup|resume|clear|compact|fork`), `PreToolUse` and `PostToolUse` (matcher = tool name regex; `if` = one permission rule), `Stop`, `Notification` (matcher = `permission_prompt|idle_prompt|…`), `InstructionsLoaded` (matcher = load reason; disabled). Others documented for reference: `Setup`, `UserPromptSubmit`, `PermissionRequest`, `PostToolUseFailure`, `SubagentStart/Stop`, `PreCompact/PostCompact`, `SessionEnd`, `FileChanged`, `ConfigChange`, `WorktreeCreate/Remove`.

## Input, output, exit codes

- Input: JSON on stdin with `session_id`, `cwd`, `hook_event_name`, `permission_mode`, plus event fields (`tool_name`, `tool_input`, `tool_response`, `source`, `stop_hook_active`, `message`, `file_path`, `load_reason` …).
- Exit 0 + JSON on stdout = structured control. Exit 2 = block, stderr is the reason (PreToolUse: shown to Claude; Stop: Claude continues with it). Other codes = non-blocking error. Choose one style per hook.
- JSON fields: universal `continue`, `stopReason`, `systemMessage`, `terminalSequence`; `hookSpecificOutput.hookEventName` + event fields: `permissionDecision` (`allow|deny|ask|defer`) + `permissionDecisionReason`, `updatedInput`, `additionalContext` (PreToolUse/PostToolUse/SessionStart/Stop…), top-level `decision: "block"` + `reason` (Stop, PostToolUse). Output strings are capped at 10,000 characters.
- `timeout` is in **seconds** (default 600 for command hooks). Stdout of a successful hook reaches Claude only on `SessionStart`/`UserPromptSubmit`-type events; elsewhere it goes to the debug log, and `additionalContext` is the way to speak to Claude.
- `Stop`: check `stop_hook_active`; Claude Code caps consecutive blocks at 8. `Notification`/`InstructionsLoaded`: no decision control.
- The `if` filter is **best-effort** on Bash (it runs the hook when it cannot parse the command) and matches only the named tool (gotcha #5). Hard allow/deny belongs in permissions.

## Our six hooks (+1 disabled)

| Event / matcher / `if` | Script | Fail mode | Why not a CLAUDE.md line |
|---|---|---|---|
| `SessionStart` `startup\|resume` | `session-start.sh` | open | facts are dynamic (branch, spec, k3d, Flux, age key, ports) |
| `PreToolUse` `Bash` `if: Bash(kubectl *)` | `gitops-guard.sh` | closed (exit 2 on bad input) | must inspect verb + namespace; deny rule cannot say "except flux-system" |
| `PreToolUse` `Edit\|Write` `if: Edit\|Write(deploy/**, clusters/**)` | `secret-guard.sh` | closed | must inspect content (`kind: Secret` without `sops:`) |
| `PostToolUse` `Edit\|Write` | `format.sh` | open | guaranteed, touched file only, needs no reasoning |
| `Stop` | `stop-tests.sh` | open | guardrail on "done"; blocks once per code state |
| `Notification` `permission_prompt` | `notify.sh` | open | side effect: OSC 777 `terminalSequence` + `notify-send` |
| `InstructionsLoaded` (local example only) | `instructions-loaded.sh` | open | observability for the memory lesson |

Rules applied to all: exec form, `${CLAUDE_PROJECT_DIR}` paths, explicit `timeout` (5–10 s on tool events, 120 s on Stop), no network, no model calls, logs to `.claude/logs/` (gitignored), never mutate tracked files except the formatter on the touched file, tests in `.claude/hooks/tests/run.sh` (`make test-hooks`, 29 cases).

## How to verify

- `make test-hooks` feeds sample stdin JSON and checks exit code + JSON.
- Live: `/hooks` lists them by event; `.claude/logs/hooks.log` records every decision; `claude --debug` shows hook execution. Seen on 2026-09-02: `kubectl apply -k …` denied by `gitops-guard`; a plaintext Secret write denied by `secret-guard`; `format ruff format …` after an Edit and a Write.

## Common mistakes

`type: prompt`/`agent` hooks for things that need no judgment (and cost a model call every event); repo mutation on `PreToolUse`; tree-wide formatters; Stop hooks without a marker (loop until the 8-block cap); printing to stdout on `PostToolUse` and wondering why Claude never sees it; `timeout` in milliseconds; shell form with `${CLAUDE_PROJECT_DIR}` paths containing spaces.
