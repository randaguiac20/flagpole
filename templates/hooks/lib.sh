#!/usr/bin/env bash
# Shared helpers for every hook in this directory. Source it, never execute it.
# Design rules for every hook: deterministic, idempotent, no network, no LLM calls, and log to
# .claude/logs/ (gitignored). A hook that is slow or flaky is worse than no hook: it trains everyone
# to disable hooks.

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
LOG_DIR="$PROJECT_DIR/.claude/logs"
STATE_DIR="$PROJECT_DIR/.claude/state"
mkdir -p "$LOG_DIR" "$STATE_DIR"
HOOK_NAME="$(basename "${0:-hook}" .sh)"

log() { printf '%s %s %s\n' "$(date -u +%FT%TZ)" "$HOOK_NAME" "$*" >>"$LOG_DIR/hooks.log"; }

# Read the event JSON from stdin into $INPUT. Fail-closed callers check `[[ -n "$INPUT" ]]` and jq validity.
read_input() {
  INPUT="$(cat)"
  if ! command -v jq >/dev/null 2>&1; then
    echo "$HOOK_NAME: jq is required (make bootstrap installs it)" >&2
    exit 2
  fi
  if ! jq -e . >/dev/null 2>&1 <<<"$INPUT"; then
    echo "$HOOK_NAME: hook input is not valid JSON" >&2
    exit 2
  fi
}

# jget '.tool_input.command'  -> raw string or empty
jget() { jq -r "$1 // empty" <<<"$INPUT"; }

# deny <event> <reason>: PreToolUse structured deny (exit 0 + JSON, per docs "choose one approach per hook").
deny() {
  jq -nc --arg ev "$1" --arg r "$2" \
    '{hookSpecificOutput:{hookEventName:$ev,permissionDecision:"deny",permissionDecisionReason:$r}}'
}
