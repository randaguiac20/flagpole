#!/usr/bin/env bash
# Hook tests: each hook is fed sample stdin JSON in a throwaway project dir and judged on exit code + JSON output.
# Run with `make test-hooks`. No network, no cluster, no Claude.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOOKS="$(dirname "$HERE")"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
export CLAUDE_PROJECT_DIR="$TMP"
export HOME="$TMP/home"; mkdir -p "$HOME"     # session-start must not see the real age key
mkdir -p "$TMP/deploy/base" "$TMP/docs" "$TMP/backend" "$TMP/scripts"
cp "$HOOKS/../../scripts/ports.sh" "$TMP/scripts/"; cp "$HOOKS/../../.env.example" "$TMP/"
git -C "$TMP" init -q -b main && git -C "$TMP" -c user.name=t -c user.email=t@t commit -q --allow-empty -m init

pass=0; fail=0
# check <name> <hook> <stdin-json> <want-exit> [<jq-assertion-on-stdout>|'' ] [<want-empty-stdout>]
check() {
  local name="$1" hook="$2" input="$3" want_rc="$4" want_jq="${5:-}" want_empty="${6:-}"
  local out rc ok=1
  out="$(printf '%s' "$input" | "$HOOKS/$hook" 2>"$TMP/stderr")"; rc=$?
  [[ "$rc" -eq "$want_rc" ]] || ok=0
  if [[ -n "$want_jq" ]]; then jq -e "$want_jq" >/dev/null 2>&1 <<<"$out" || ok=0; fi
  if [[ -n "$want_empty" && -n "$out" ]]; then ok=0; fi
  if (( ok )); then pass=$((pass+1)); printf '  ok   %-42s\n' "$name"
  else fail=$((fail+1)); printf '  FAIL %-42s rc=%s out=%s err=%s\n' "$name" "$rc" "${out:0:160}" "$(head -c 160 "$TMP/stderr")"; fi
}
bash_in() { jq -nc --arg c "$1" '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:$c}}'; }
write_in() { jq -nc --arg p "$1" --arg c "$2" '{hook_event_name:"PreToolUse",tool_name:"Write",tool_input:{file_path:$p,content:$c}}'; }
edit_in() { jq -nc --arg p "$1" --arg o "$2" --arg n "$3" '{hook_event_name:"PreToolUse",tool_name:"Edit",tool_input:{file_path:$p,old_string:$o,new_string:$n}}'; }
DENY='.hookSpecificOutput.permissionDecision=="deny"'

echo "gitops-guard.sh"
check "read-only get is allowed"        gitops-guard.sh "$(bash_in 'kubectl get pods -n flagpole-dev')"                          0 '' yes
check "apply into deploy/ is denied"    gitops-guard.sh "$(bash_in 'kubectl apply -k deploy/overlays/dev')"                      0 "$DENY"
check "create in flux-system allowed"   gitops-guard.sh "$(bash_in 'cat k | kubectl -n flux-system create secret generic sops-age --from-file=age.agekey=/dev/stdin')" 0 '' yes
check "namespace=flux-system allowed"   gitops-guard.sh "$(bash_in 'kubectl create ns x --namespace=flux-system')"               0 '' yes
check "rollout restart denied"          gitops-guard.sh "$(bash_in 'kubectl rollout restart deploy/flagpole-api -n flagpole-dev')" 0 "$DENY"
check "rollout status allowed"          gitops-guard.sh "$(bash_in 'kubectl rollout status deploy/flagpole-api -n flagpole-dev')"  0 '' yes
check "compound command scale denied"   gitops-guard.sh "$(bash_in 'make deploy && kubectl scale deploy x --replicas=0 -n flagpole-prod')" 0 "$DENY"
check "non-kubectl command ignored"     gitops-guard.sh "$(bash_in 'flux reconcile kustomization flagpole-dev --with-source')"     0 '' yes
check "invalid JSON fails closed (2)"   gitops-guard.sh 'not json'                                                                 2

echo "secret-guard.sh"
PLAIN=$'apiVersion: v1\nkind: Secret\nmetadata:\n  name: db\nstringData:\n  password: hunter2\n'
ENC=$'apiVersion: v1\nkind: Secret\nmetadata:\n  name: db\nstringData:\n  password: ENC[AES256_GCM,data:abc,iv:def,tag:ghi,type:str]\nsops:\n  age:\n    - recipient: age1abc\n  version: 3.13.3\n'
CM=$'apiVersion: v1\nkind: ConfigMap\nmetadata:\n  name: c\ndata:\n  a: b\n'
check "plaintext Secret under deploy/ denied"   secret-guard.sh "$(write_in "$TMP/deploy/base/db.yaml" "$PLAIN")"      0 "$DENY"
check "encrypted Secret allowed"                 secret-guard.sh "$(write_in "$TMP/deploy/base/db.yaml" "$ENC")"        0 '' yes
check "ConfigMap allowed"                        secret-guard.sh "$(write_in "$TMP/deploy/base/cm.yaml" "$CM")"         0 '' yes
check "plaintext outside deploy/ ignored"        secret-guard.sh "$(write_in "$TMP/docs/example.yaml" "$PLAIN")"        0 '' yes
check "multi-doc: one plaintext doc denied"      secret-guard.sh "$(write_in "$TMP/deploy/base/all.yaml" "$CM---
$PLAIN")" 0 "$DENY"
printf '%s' "$ENC" > "$TMP/deploy/base/edit.yaml"
check "edit that strips sops block denied"       secret-guard.sh "$(edit_in "$TMP/deploy/base/edit.yaml" $'sops:\n  age:\n    - recipient: age1abc\n  version: 3.13.3\n' '')" 0 "$DENY"
check "edit keeping envelope allowed"            secret-guard.sh "$(edit_in "$TMP/deploy/base/edit.yaml" 'name: db' 'name: db2')" 0 '' yes
check "non-yaml path ignored"                    secret-guard.sh "$(write_in "$TMP/deploy/README.md" "$PLAIN")"          0 '' yes

echo "format.sh"
printf 'x = { "a":1 }\n' > "$TMP/backend/bad.py"
check "formats touched .py, no stdout" format.sh "$(jq -nc --arg p "$TMP/backend/bad.py" '{hook_event_name:"PostToolUse",tool_name:"Write",tool_input:{file_path:$p}}')" 0 '' yes
if command -v ruff >/dev/null; then
  if [[ "$(cat "$TMP/backend/bad.py")" == 'x = {"a": 1}' ]]; then pass=$((pass+1)); echo "  ok   ruff rewrote the file"; else fail=$((fail+1)); echo "  FAIL ruff did not rewrite: $(cat "$TMP/backend/bad.py")"; fi
else echo "  skip ruff not installed"; fi
check "missing file is a no-op" format.sh "$(jq -nc --arg p "$TMP/nope.py" '{tool_input:{file_path:$p}}')" 0 '' yes

echo "stop-tests.sh"
git -C "$TMP" add -A >/dev/null && git -C "$TMP" -c user.name=t -c user.email=t@t commit -q -m "fixtures" >/dev/null   # clean tree baseline
printf 'test-fast:\n\t@echo "1 failed"; exit 1\n' > "$TMP/Makefile"
check "stop_hook_active short-circuits"   stop-tests.sh '{"hook_event_name":"Stop","stop_hook_active":true}'  0 '' yes
check "clean tree: nothing runs"          stop-tests.sh '{"hook_event_name":"Stop","stop_hook_active":false}' 0 '' yes
echo "print(1)" > "$TMP/backend/app.py"
check "failing tests block once"          stop-tests.sh '{"hook_event_name":"Stop","stop_hook_active":false}' 0 '.decision=="block" and (.reason|test("test-fast"))'
check "same state does not block twice"   stop-tests.sh '{"hook_event_name":"Stop","stop_hook_active":false}' 0 '' yes
printf 'test-fast:\n\t@echo ok\n' > "$TMP/Makefile"; echo "print(2)" > "$TMP/backend/app.py"
check "new state with passing tests"      stop-tests.sh '{"hook_event_name":"Stop","stop_hook_active":false}' 0 '' yes

echo "notify.sh"
check "emits OSC 777 terminalSequence" notify.sh '{"hook_event_name":"Notification","notification_type":"permission_prompt","message":"Claude needs your permission"}' 0 '.terminalSequence|test("777;notify;.*permission")'

echo "session-start.sh"
check "startup context has branch and key state" session-start.sh '{"hook_event_name":"SessionStart","source":"startup"}' 0 '.hookSpecificOutput.additionalContext|test("Branch: main") and test("age key: missing")'

# The flux line reads a positional awk field out of `flux get kustomizations -A`, and for months it
# read $4 (SUSPENDED) instead of $5 (READY): a healthy cluster reported =False on every session, and
# a suspended one would have reported =True. Nothing caught it because the harness has no cluster,
# so the probe never ran. Stubbing k3d and flux makes it run, with the real column layout.
echo "session-start.sh (cluster probe, stubbed)"
mkdir -p "$TMP/bin"
cat > "$TMP/bin/k3d" <<'STUB'
#!/usr/bin/env bash
echo '[{"name":"flagpole","serversRunning":1,"serversCount":1}]'
STUB
# NAMESPACE NAME REVISION SUSPENDED READY MESSAGE — tab separated, as flux emits it.
cat > "$TMP/bin/flux" <<'STUB'
#!/usr/bin/env bash
printf 'flux-system\tflagpole-dev\tmain@sha1:abc\tFalse\tTrue\tApplied revision: main@sha1:abc\n'
printf 'flux-system\tplatform\tmain@sha1:abc\tTrue\tFalse\tSuspended\n'
STUB
chmod +x "$TMP/bin/k3d" "$TMP/bin/flux"
PATH="$TMP/bin:$PATH" check "reports READY, not SUSPENDED" session-start.sh \
  '{"hook_event_name":"SessionStart","source":"startup"}' 0 \
  '.hookSpecificOutput.additionalContext|test("flagpole-dev=True") and test("platform=False")'

echo "instructions-loaded.sh"
check "appends a log line" instructions-loaded.sh "$(jq -nc --arg p "$TMP/CLAUDE.md" '{hook_event_name:"InstructionsLoaded",file_path:$p,memory_type:"Project",load_reason:"session_start"}')" 0 '' yes
if grep -q "session_start.*Project.*CLAUDE.md" "$TMP/.claude/logs/instructions-loaded.log" 2>/dev/null; then pass=$((pass+1)); echo "  ok   log line present"; else fail=$((fail+1)); echo "  FAIL log line missing"; fi

echo; echo "hook tests: $pass passed, $fail failed"
(( fail == 0 ))
