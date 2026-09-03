#!/usr/bin/env bash
# PreToolUse(Edit|Write): refuse a write whose CONTENT is wrong — the case a permission rule cannot
# express, because `permissions.deny` matches paths and commands, never what is inside them.
#
# Fail-closed: unreadable input or an error exits 2 and blocks. A guard that fails open is decoration.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input

path="$(jget .tool_input.file_path)"
[[ -z "$path" ]] && exit 0
rel="${path#"$PROJECT_DIR"/}"

# The `if:` filter in settings.json is best-effort by design, so re-check the path here.
GUARDED="protected-dir"          # <-- the directory this guard protects
case "$rel" in "$GUARDED"/*) ;; *) exit 0 ;; esac

# Reconstruct the content this call WOULD produce — for Write it is the payload, for Edit it is the
# file with the replacement applied. Checking the file on disk instead would inspect the old content.
content="$(HOOK_INPUT="$INPUT" python3 - "$path" <<'PY'
import json, os, sys
inp = json.loads(os.environ["HOOK_INPUT"]); ti = inp.get("tool_input", {})
if inp.get("tool_name") == "Write":
    print(ti.get("content", ""), end="")
else:
    try: c = open(sys.argv[1], encoding="utf-8").read()
    except OSError: c = ""
    old, new = ti.get("old_string", ""), ti.get("new_string", "")
    if old:
        c = c.replace(old, new) if ti.get("replace_all") else c.replace(old, new, 1)
    print(c, end="")
PY
)" || { echo "content-guard: could not evaluate $rel" >&2; exit 2; }

FORBIDDEN='THE PATTERN THAT MUST NOT BE WRITTEN'   # <-- an ERE, not a glob
if grep -qE "$FORBIDDEN" <<<"$content"; then
  log "deny $rel"
  deny PreToolUse "content-guard: $rel WHAT IS WRONG. WHAT TO DO INSTEAD, as a command they can run."
  exit 0
fi
exit 0
