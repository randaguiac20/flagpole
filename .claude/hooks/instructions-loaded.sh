#!/usr/bin/env bash
# InstructionsLoaded (documented, DISABLED by default): append one line per CLAUDE.md / rule load to
# .claude/logs/instructions-loaded.log. Observability only; the event has no decision control.
# Enable locally by copying the hook block from .claude/settings.local.json.example.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
printf '%s %-16s %-8s %s\n' "$(date -u +%FT%TZ)" "$(jget .load_reason)" "$(jget .memory_type)" \
  "${INPUT_PATH:-$(jget .file_path)}$( g="$(jget .globs)"; [[ -n "$g" ]] && printf ' globs=%s' "$(jq -c '.globs' <<<"$INPUT")")" \
  >>"$LOG_DIR/instructions-loaded.log"
exit 0
