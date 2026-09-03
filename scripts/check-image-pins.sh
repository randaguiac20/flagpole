#!/usr/bin/env bash
# Every base image must be named by digest. Spec: 005-platform-delivery FR-002 (T010a).
#
# A tag is a moving target: python:3.12-slim today and in six months are different software with the
# same name. A digest makes that difference appear in a diff, which is the only place anyone will
# notice it. Runs in scripts/build.sh, in pre-commit and in CI.
#
# Prove it still bites before trusting it:
#   printf 'FROM alpine\n' > /tmp/Dockerfile.probe && scripts/check-image-pins.sh /tmp/Dockerfile.probe
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

files=("$@")
if [[ ${#files[@]} -eq 0 ]]; then
  mapfile -t files < <(cd "$ROOT" && git ls-files '*Dockerfile' '*Dockerfile.*' 2>/dev/null)
  files=("${files[@]/#/$ROOT/}")
fi

rc=0
for file in "${files[@]}"; do
  [[ -f "$file" ]] || continue
  # `FROM <image> [AS stage]` and `COPY --from=<image>`. The trailing `+` matters: `[^ ]*` after an
  # alternation that does not consume the space matches the empty string, and the check then passes
  # while inspecting nothing — which is exactly what it did on the first attempt.
  while read -r image; do
    # A stage name (COPY --from=build) is not an image and has nothing to pin.
    [[ "$image" == *[:/]* ]] || continue
    if [[ "$image" != *"@sha256:"* ]]; then
      printf 'UNPINNED BASE: %s names %s without a digest (FR-002)\n' "${file#"$ROOT"/}" "$image" >&2
      rc=1
    fi
  done < <(grep -hoP '^(FROM[[:space:]]+|COPY[[:space:]]+--from=)\K[^[:space:]]+' "$file")
done

exit $rc
