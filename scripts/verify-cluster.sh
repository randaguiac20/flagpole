#!/usr/bin/env bash
# Asserts a running Flagpole cluster against specs/005-platform-delivery/contracts/cluster-contract.json.
# Spec: 005-platform-delivery (T001, T042). Read-only: it inspects, and the one admission check it
# makes is server-side dry-run, which creates nothing. The deploy-verifier agent reads the same
# contract, so the script and the agent cannot drift.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/specs/005-platform-delivery/contracts/cluster-contract.json"
pass=0 fail=0

ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail + 1)); }
note() { printf '\n\033[1m%s\033[0m\n' "$1"; }

q() { jq -r "$1" "$CONTRACT"; }

check() { # check <description> <command...>
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$what"; else bad "$what"; fi
}

refuse() { # refuse <description> <command...> — passes when the command FAILS
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then bad "$what"; else ok "$what"; fi
}

[[ -r "$CONTRACT" ]] || { echo "contract not found: $CONTRACT" >&2; exit 2; }
command -v jq >/dev/null || { echo "jq is required" >&2; exit 2; }

ready() { # ready <namespace> <kind> <name>
  kubectl -n "$1" get "$2" "$3" \
    -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}' 2>/dev/null | grep -qx True
}

note "cluster"
cluster="$(q .cluster_name)"
check "k3d cluster '$cluster' exists" \
  bash -c "k3d cluster list -o json | jq -e '.[] | select(.name == \"$cluster\")'"
check "the API server answers" kubectl cluster-info

note "reconciliation units"
while read -r unit; do
  check "Kustomization/$unit is Ready" ready flux-system kustomization "$unit"
done < <(q '.flux.kustomizations[]')

note "platform components"
while read -r name ns version; do
  check "HelmRelease/$name in $ns is Ready" ready "$ns" helmrelease "$name"
  check "HelmRelease/$name is pinned to $version" bash -c \
    "kubectl -n '$ns' get helmrelease '$name' -o jsonpath='{.spec.chart.spec.version}' | grep -qx '$version'"
done < <(q '.flux.helmreleases[] | "\(.name) \(.namespace) \(.version)"')

note "workloads"
while read -r ns; do
  while read -r kind name; do
    check "$kind/$name in $ns is available" \
      kubectl -n "$ns" rollout status "${kind,,}/$name" --timeout=5s
  done < <(q '.workloads[] | select(.per_environment) | "\(.kind) \(.name)"')
done < <(q '.environments[].namespace')

note "security"
standard="$(q .security.pod_security_standard)"
# A Pod the standard forbids, submitted with --dry-run=server: admission runs, nothing is created.
privileged='{"spec":{"containers":[{"name":"probe","image":"busybox","securityContext":{"privileged":true}}]}}'
while read -r ns; do
  check "$ns enforces the $standard standard" bash -c \
    "kubectl get ns '$ns' -o jsonpath='{.metadata.labels.pod-security\\.kubernetes\\.io/enforce}' | grep -qx '$standard'"
  check "$ns denies ingress by default" bash -c \
    "kubectl -n '$ns' get networkpolicy -o json | jq -e '[.items[] | select(.spec.policyTypes | index(\"Ingress\")) | select(.spec.podSelector == {})] | length > 0'"
  refuse "$ns rejects a privileged Pod" \
    kubectl -n "$ns" run pss-probe --image=busybox --restart=Never \
      --overrides="$privileged" --dry-run=server
done < <(q '.security.enforced_on[]')

note "environment isolation"
# Reached from a workload that is already running, rather than by creating one: this script does not
# put anything into a namespace Flux owns.
while read -r from to port; do
  refuse "$from cannot reach $to on $port" \
    kubectl -n "$from" exec deploy/flagpole-api -c flagpole-api -- \
      python -c "import socket,sys; socket.create_connection(('postgres.$to.svc.cluster.local', $port), 5)"
done < <(q '.security.network.denied_examples[] | "\(.from) \(.to) \(.port)"')

note "the operator grant is where it belongs"
while read -r ns granted; do
  # Absent deployment must not read as "grants nothing": that would pass against an empty cluster.
  if ! kubectl -n "$ns" get deploy flagpole-api >/dev/null 2>&1; then
    bad "$ns grants the assistant operator rights: no flagpole-api to ask"
    continue
  fi
  # The setting arrives through envFrom, so it lives in the ConfigMap the Deployment names, not in
  # an inline env entry. Reading the wrong place made dev fail and — worse — made prod pass for a
  # reason that had nothing to do with the grant.
  cm="$(kubectl -n "$ns" get deploy flagpole-api \
    -o jsonpath='{.spec.template.spec.containers[0].envFrom[0].configMapRef.name}' 2>/dev/null)"
  if [[ -z "$cm" ]]; then
    bad "$ns grants the assistant operator rights: flagpole-api names no ConfigMap"
    continue
  fi
  present="$(kubectl -n "$ns" get configmap "$cm" \
    -o jsonpath='{.data.FLAGPOLE_OPERATOR_SERVICE_ISSUER}' 2>/dev/null)"
  if { [[ "$granted" == "true" && -n "$present" ]] || [[ "$granted" == "false" && -z "$present" ]]; }; then
    ok "$ns grants the assistant operator rights: $granted"
  else
    bad "$ns grants the assistant operator rights: expected $granted, found '${present:-<absent>}'"
  fi
done < <(q '.environments[] | "\(.namespace) \(.grants_operator_to_mcp)"')

note "hosts answer over TLS"
while read -r host; do
  check "https://$host answers" curl -sk --max-time 10 -o /dev/null "https://$host/"
  check "http://$host redirects to TLS" bash -c \
    "curl -s --max-time 10 -o /dev/null -w '%{http_code}' 'http://$host/' | grep -qE '^30[128]\$'"
done < <(q '[.environments[].hosts | to_entries[].value] + [.shared_hosts | to_entries[].value] | .[]' | sort -u)

note "secrets"
check "the decryption key is in the cluster" \
  kubectl -n "$(q .secrets.decryption_secret.namespace)" get secret "$(q .secrets.decryption_secret.name)"
check "no plaintext Secret is committed" "$ROOT/scripts/check-sops-secrets.sh"

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
