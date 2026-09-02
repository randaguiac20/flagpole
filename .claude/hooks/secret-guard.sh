#!/usr/bin/env bash
# PreToolUse(Edit|Write, if: "Edit(deploy/**)"): deny writing a kind: Secret with data/stringData but no SOPS envelope
# under deploy/ or clusters/. Needs the file CONTENT, which a permission rule cannot inspect.
# The `if` filter is best-effort by design (docs), so the script re-checks the path itself. Fail-closed on bad input.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
path="$(jget .tool_input.file_path)"
[[ -z "$path" ]] && exit 0
rel="${path#"$PROJECT_DIR"/}"
case "$rel" in deploy/*|clusters/*) ;; *) exit 0 ;; esac
case "$path" in *.yaml|*.yml) ;; *) exit 0 ;; esac

# Compute the content the file WOULD have after this tool call, then scan each YAML document.
verdict="$(HOOK_INPUT="$INPUT" python3 - "$path" <<'PY'
import json, os, re, sys
inp = json.loads(os.environ["HOOK_INPUT"])
path = sys.argv[1]
ti = inp.get("tool_input", {})
if inp.get("tool_name") == "Write":
    content = ti.get("content", "")
else:
    try:
        content = open(path, encoding="utf-8").read()
    except OSError:
        content = ""
    old, new = ti.get("old_string", ""), ti.get("new_string", "")
    if old:
        content = content.replace(old, new) if ti.get("replace_all") else content.replace(old, new, 1)
bad = []
for i, doc in enumerate(re.split(r"^---\s*$", content, flags=re.M)):
    if not re.search(r"^kind:\s*Secret\s*$", doc, re.M):
        continue
    has_data = re.search(r"^(data|stringData):", doc, re.M)
    has_sops = re.search(r"^sops:", doc, re.M) and "ENC[" in doc
    if has_data and not has_sops:
        bad.append(str(i + 1))
print("PLAINTEXT " + ",".join(bad) if bad else "OK")
PY
)"
case "$verdict" in
  OK) exit 0 ;;
  PLAINTEXT*)
    log "deny $rel (document(s) ${verdict#PLAINTEXT })"
    deny PreToolUse "secret-guard: $rel contains a kind: Secret with plaintext data/stringData (document ${verdict#PLAINTEXT }). Commit only SOPS-encrypted secrets: write the plaintext OUTSIDE deploy/ (e.g. .claude/logs/tmp-secret.yaml), run 'sops --encrypt --in-place <file>', then move it under deploy/. See docs/secrets-sops.md."
    exit 0 ;;
  *) echo "secret-guard: could not evaluate $rel ($verdict)" >&2; exit 2 ;;
esac
