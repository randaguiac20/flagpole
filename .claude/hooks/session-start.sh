#!/usr/bin/env bash
# SessionStart (startup|resume): inject facts that change between sessions and would go stale in CLAUDE.md.
# Output: JSON additionalContext (~15 lines). Every probe is time-boxed; the hook never fails the session (fail-open).
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
cd "$PROJECT_DIR" || exit 0

branch="$(git branch --show-current 2>/dev/null || echo '?')"
dirty="$(git status --porcelain 2>/dev/null | wc -l | tr -d ' ')"
spec="none (chores on main)"
[[ "$branch" =~ ^[0-9]{3}- ]] && spec="$branch (specs/$branch/)"

cluster="$(grep -E '^FLAGPOLE_CLUSTER_NAME=' .env 2>/dev/null | cut -d= -f2)"
cluster="${cluster:-flagpole}"
k3d_state="k3d CLI not installed"
if command -v k3d >/dev/null 2>&1; then
  k3d_state="$(timeout 3 k3d cluster list -o json 2>/dev/null \
    | jq -r --arg n "$cluster" '.[] | select(.name==$n) | "\(.serversRunning)/\(.serversCount) servers running"' 2>/dev/null)"
  k3d_state="${k3d_state:-cluster '$cluster' not created (make cluster-up)}"
fi

flux_state="n/a (no cluster)"
if [[ "$k3d_state" == *running* ]] && command -v flux >/dev/null 2>&1; then
  flux_state="$(timeout 4 flux --context "k3d-$cluster" get kustomizations -A --no-header 2>/dev/null \
    | awk '{printf "%s=%s ", $2, $4}')"
  flux_state="${flux_state:-flux not bootstrapped}"
fi

key_file="$(grep -E '^SOPS_AGE_KEY_FILE=' .env 2>/dev/null || grep -E '^SOPS_AGE_KEY_FILE=' .env.example 2>/dev/null | head -1)"
key_file="${key_file#*=}"; key_file="${key_file/#\~/$HOME}"
if [[ -n "$key_file" && -s "$key_file" ]]; then age_state="present at ${key_file/#$HOME/~} (never read it)"; else age_state="missing (make bootstrap creates it)"; fi

ports="$(scripts/ports.sh table 2>/dev/null | tail -n +2 | awk '{printf "%s:%s(%s) ", $1, $2, $3}')"

ctx="$(cat <<TXT
Session facts ($(date -u +%F) $(jget .source)):
- Branch: $branch | uncommitted files: $dirty | active spec: $spec
- k3d '$cluster': $k3d_state
- Flux kustomizations: $flux_state
- SOPS age key: $age_state
- Dev ports: ${ports:-see .env.example}
TXT
)"
log "source=$(jget .source) branch=$branch k3d='$k3d_state'"
jq -nc --arg c "$ctx" '{hookSpecificOutput:{hookEventName:"SessionStart",additionalContext:$c}}'
