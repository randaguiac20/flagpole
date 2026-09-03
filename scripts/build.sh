#!/usr/bin/env bash
# Builds the three container images. Spec: 005-platform-delivery FR-001, FR-002 (T010).
#
# Lints each Dockerfile first, then builds, then prints what was actually produced — including the
# base digest each image was built from, so "pinned by digest" is something a reader can see rather
# than something the comments claim.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# shellcheck disable=SC1091
[[ -f .env ]] && source .env
REGISTRY="${FLAGPOLE_IMAGE_REGISTRY:-ghcr.io/randaguiac20}"
TAG="${FLAGPOLE_IMAGE_TAG:-0.1.0}"

services=(api:backend consumer:consumer web:frontend)

echo "== lint"
for pair in "${services[@]}"; do
  dir="${pair#*:}"
  hadolint "$dir/Dockerfile"
  echo "  hadolint  $dir/Dockerfile  clean"
done

echo
echo "== bases (every FROM must name a digest — FR-002)"
if ! "$ROOT/scripts/check-image-pins.sh" backend/Dockerfile consumer/Dockerfile frontend/Dockerfile; then
  echo "refusing to build: see FR-002 and docs/dependencies.md" >&2
  exit 1
fi
for pair in "${services[@]}"; do
  dir="${pair#*:}"
  grep -hoP '^FROM[[:space:]]+\K[^[:space:]]+' "$dir/Dockerfile" | while read -r image; do
    printf '  %-12s %s\n' "$dir" "$image"
  done
done

echo
echo "== build"
for pair in "${services[@]}"; do
  name="${pair%%:*}"; dir="${pair#*:}"
  image="$REGISTRY/flagpole-$name:$TAG"
  echo "  building $image"
  docker build --quiet --tag "$image" "$dir" >/dev/null
done

echo
echo "== built"
printf '  %-45s %-12s %s\n' IMAGE SIZE ID
for pair in "${services[@]}"; do
  name="${pair%%:*}"
  image="$REGISTRY/flagpole-$name:$TAG"
  read -r size id < <(docker image inspect "$image" --format '{{.Size}} {{.Id}}')
  printf '  %-45s %-12s %s\n' "$image" "$(numfmt --to=iec "$size")" "${id#sha256:}" | cut -c1-95
done

echo
echo "next: make deploy (imports these into the k3d cluster and reconciles)"
