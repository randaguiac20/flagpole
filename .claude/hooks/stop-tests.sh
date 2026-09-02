#!/usr/bin/env bash
# Stop: run the fast test subset when service code changed, and block the turn ONCE per code state if it fails.
# Loop protection: (1) stop_hook_active => exit 0, (2) a fingerprint of the working tree is stored in .claude/state,
# so the same failing state never blocks twice, (3) nothing changed => nothing runs. Timeout in settings.json.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
[[ "$(jget .stop_hook_active)" == "true" ]] && exit 0
cd "$PROJECT_DIR" || exit 0
WATCH=(backend consumer mcp frontend/src .claude/hooks)
status="$(git status --porcelain -- "${WATCH[@]}" 2>/dev/null)"
[[ -z "$status" ]] && exit 0            # no uncommitted service changes: CI covers commits
fp="$( { echo "$status"; git diff HEAD -- "${WATCH[@]}" 2>/dev/null; } | sha256sum | cut -c1-16)"
marker="$STATE_DIR/stop-tests.last"
if [[ -f "$marker" && "$(cut -d' ' -f1 "$marker")" == "$fp" ]]; then
  exit 0                                # already judged this exact state (passed, or blocked once)
fi
out="$(timeout 100 make -s test-fast 2>&1)"; rc=$?
echo "$fp $([[ $rc -eq 0 ]] && echo pass || echo fail)" >"$marker"
printf '%s\n' "$out" >"$LOG_DIR/stop-tests.log"
log "fingerprint=$fp rc=$rc"
if (( rc != 0 )); then
  reason="Stop hook: 'make test-fast' failed for the current changes. Fix it or explain why it cannot be fixed, then finish. Last lines:
$(tail -n 20 <<<"$out")"
  jq -nc --arg r "$reason" '{decision:"block",reason:$r}'
fi
exit 0
