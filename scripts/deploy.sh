#!/usr/bin/env bash
# Supplies the images to the cluster and waits for the reconciler. Spec: 005-platform-delivery
# FR-005, FR-020 (T025).
#
# It applies nothing. Everything the cluster runs comes from git; this script only puts the locally
# built images where the cluster can find them and then waits on a condition — never on a sleep.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
[[ -f .env ]] && source .env
CLUSTER="${FLAGPOLE_CLUSTER_NAME:-flagpole}"
REGISTRY="${FLAGPOLE_IMAGE_REGISTRY:-ghcr.io/randaguiac20}"
TAG="${FLAGPOLE_IMAGE_TAG:-0.1.0}"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
die() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

k3d cluster list -o json | jq -e --arg n "$CLUSTER" '.[] | select(.name == $n)' >/dev/null 2>&1 \
  || die "no k3d cluster called '$CLUSTER' — run: make cluster-up"

say "images"
images=()
for name in api consumer web; do
  image="$REGISTRY/flagpole-$name:$TAG"
  docker image inspect "$image" >/dev/null 2>&1 || die "$image is not built — run: make build"
  images+=("$image")
  echo "  $image"
done
# Imported rather than pulled: feature 006 publishes these, and then the manifests work unchanged
# because they already name the published image and pull only if it is absent (research E11).
k3d image import --cluster "$CLUSTER" "${images[@]}"

say "reconcile"
# --with-source so the cluster fetches the current commit rather than re-applying the last one.
flux reconcile source git flux-system
for unit in platform flagpole-dev flagpole-prod; do
  echo "  $unit"
  flux reconcile kustomization "$unit" --with-source || die "$unit did not reconcile — flux get kustomizations"
done

say "wait"
# On conditions, never on a sleep: a sleep is a guess that is either wrong or slow.
kubectl -n flux-system wait kustomization/platform --for=condition=Ready --timeout=10m
for env in dev prod; do
  kubectl -n flux-system wait "kustomization/flagpole-$env" --for=condition=Ready --timeout=10m
  kubectl -n "flagpole-$env" rollout status deploy/flagpole-api --timeout=5m
  kubectl -n "flagpole-$env" rollout status deploy/flagpole-consumer --timeout=5m
  kubectl -n "flagpole-$env" rollout status deploy/flagpole-web --timeout=5m
done

say "state"
flux get kustomizations
flux get helmreleases --all-namespaces

say "next"
cat <<'MSG'
  scripts/verify-cluster.sh        assert the cluster against its contract
  https://dev.flagpole.localhost   sign in as alice@flagpole.local / flagpole
MSG
