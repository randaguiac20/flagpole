#!/usr/bin/env bash
# PostToolUse(Edit|Write): format the file that was just touched. Fail-OPEN — the opposite of a
# guard. A formatter that blocks the turn because it is not installed is a formatter people remove.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input

path="$(jget .tool_input.file_path)"
[[ -f "$path" ]] || exit 0

case "$path" in
  *.py) command -v ruff >/dev/null && ruff format --quiet "$path" >>"$LOG_DIR/format.log" 2>&1 \
          && log "ruff format ${path#"$PROJECT_DIR"/}" ;;
  *.ts|*.tsx|*.js|*.json|*.css|*.md) : ;;   # <your formatter here>
esac
exit 0
