#!/usr/bin/env bash
# PreToolUse(Bash, if: "Bash(kubectl *)"): deny kubectl commands that mutate anything outside flux-system.
# Why a hook and not permissions.deny: the rule depends on the verb AND the namespace argument ("except flux-system"),
# which permission-rule syntax cannot express. Plain blocks (kubectl delete) live in permissions.deny.
# Fail-closed: unreadable input -> exit 2.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
cmd="$(jget .tool_input.command)"
[[ -z "$cmd" ]] && exit 0

MUTATING='^(apply|create|edit|patch|replace|scale|set|label|annotate|expose|run|drain|cordon|uncordon|taint)$'
ROLLOUT_MUTATING='^(restart|undo|pause|resume)$'

# Split compound commands on && || ; | and newlines; inspect each part that invokes kubectl.
mapfile -t parts < <(sed -E 's/(&&|\|\||;|\|)/\n/g' <<<"$cmd")
for part in "${parts[@]}"; do
  read -r -a tok <<<"$part"
  i=0; n=${#tok[@]}
  while (( i < n )) && [[ "${tok[$i]}" != "kubectl" ]]; do ((i++)); done
  (( i >= n )) && continue
  verb=""; ns=""; j=$((i+1))
  while (( j < n )); do
    t="${tok[$j]}"
    case "$t" in
      -n|--namespace) ns="${tok[$((j+1))]:-}"; j=$((j+2)); continue ;;
      --namespace=*) ns="${t#--namespace=}"; j=$((j+1)); continue ;;
      -n=*) ns="${t#-n=}"; j=$((j+1)); continue ;;
      --context|--kubeconfig|-s|--server|--cluster|--user) j=$((j+2)); continue ;;
      -*) j=$((j+1)); continue ;;
    esac
    if [[ -z "$verb" ]]; then
      verb="$t"
      if [[ "$verb" == "rollout" ]]; then
        sub="${tok[$((j+1))]:-}"
        [[ "$sub" =~ $ROLLOUT_MUTATING ]] && verb="rollout $sub" || verb="rollout-readonly"
      fi
    fi
    j=$((j+1))
  done
  [[ -z "$verb" ]] && continue
  if [[ "$verb" =~ $MUTATING || "$verb" == rollout\ * ]]; then
    if [[ "$ns" == "flux-system" ]]; then
      log "allow (flux-system): $part"
      continue
    fi
    log "deny: $part"
    deny PreToolUse "gitops-guard: 'kubectl $verb' outside flux-system is denied. Flux owns this cluster: edit the manifest under deploy/, commit, then run 'flux reconcile kustomization <name> --with-source'. Bootstrap-time objects (e.g. the sops-age secret) go in -n flux-system."
    exit 0
  fi
done
exit 0
