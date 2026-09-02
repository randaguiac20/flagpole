#!/usr/bin/env bash
# PostToolUse(Edit|Write, if: Edit(**/*.py) / Edit(**/*.ts) / Edit(**/*.tsx)): format ONLY the touched file.
# Fail-open: a missing formatter is logged, never surfaced. No stdout (PostToolUse stdout only reaches the debug log).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
path="$(jget .tool_input.file_path)"
[[ -f "$path" ]] || exit 0
case "$path" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format --quiet "$path" >>"$LOG_DIR/format.log" 2>&1 && log "ruff format ${path#"$PROJECT_DIR"/}" || log "ruff format FAILED ${path#"$PROJECT_DIR"/}"
    else
      log "skip ${path#"$PROJECT_DIR"/}: ruff not installed (uv tool install ruff)"
    fi ;;
  *.ts|*.tsx)
    fe="$PROJECT_DIR/frontend"
    if [[ -x "$fe/node_modules/.bin/prettier" ]]; then
      (cd "$fe" && node_modules/.bin/prettier --log-level warn --write "$path") >>"$LOG_DIR/format.log" 2>&1 \
        && log "prettier ${path#"$PROJECT_DIR"/}" || log "prettier FAILED ${path#"$PROJECT_DIR"/}"
    else
      log "skip ${path#"$PROJECT_DIR"/}: frontend/node_modules missing (make bootstrap)"
    fi ;;
esac
exit 0
