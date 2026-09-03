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

  # The stage names this file declares, from `FROM <image> AS <name>`. Collected first, because
  # deciding "is this token a stage or an image?" by punctuation is wrong: `FROM alpine` has no
  # colon and no slash, and the old `*[:/]*` test skipped it as if it were a stage name. It is an
  # unpinned base image with an implicit :latest — the single worst case this script exists to
  # catch — and the probe in the header above returned 0 for it. A check that cannot fail is not a
  # check; see gotchas #37 and #42.
  mapfile -t stages < <(grep -hoiP '^FROM[[:space:]]+\S+[[:space:]]+AS[[:space:]]+\K\S+' "$file" \
    | tr '[:upper:]' '[:lower:]')

  # `FROM <image> [AS stage]` and `COPY --from=<image>`. The trailing `+` matters: `[^ ]*` after an
  # alternation that does not consume the space matches the empty string, and the check then passes
  # while inspecting nothing — which is exactly what it did on the first attempt.
  while read -r image; do
    # A reference to a stage this same file declares is not an image and has nothing to pin.
    is_stage=0
    for stage in ${stages[@]+"${stages[@]}"}; do
      [[ "${image,,}" == "$stage" ]] && { is_stage=1; break; }
    done
    [[ $is_stage -eq 1 ]] && continue
    if [[ "$image" != *"@sha256:"* ]]; then
      printf 'UNPINNED BASE: %s names %s without a digest (FR-002)\n' "${file#"$ROOT"/}" "$image" >&2
      rc=1
    fi
  done < <(grep -hoP '^(FROM[[:space:]]+|COPY[[:space:]]+--from=)\K[^[:space:]]+' "$file")
done

exit $rc
