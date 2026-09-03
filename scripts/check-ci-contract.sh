#!/usr/bin/env bash
# Asserts the workflows and configuration against
# specs/006-ci-and-security/contracts/ci-contract.json. Spec: 006-ci-and-security (T001).
#
# Read-only, and it runs anywhere: it inspects files, never the network and never a cluster. This is
# the check that exists before the thing it checks — run it now, against a repository with no
# workflows, and it fails loudly. A check that has never failed has not been tested.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONTRACT="$ROOT/specs/006-ci-and-security/contracts/ci-contract.json"
cd "$ROOT" || exit 2
pass=0 fail=0

ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail + 1)); }
note() { printf '\n\033[1m%s\033[0m\n' "$1"; }

q()  { jq -r "$1" "$CONTRACT"; }
qc() { jq -c "$1" "$CONTRACT"; }   # one compact JSON object per line

check() { # check <description> <command...> — passes when the command SUCCEEDS
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then ok "$what"; else bad "$what"; fi
}

refuse() { # refuse <description> <command...> — passes when the command FAILS
  local what="$1"; shift
  if "$@" >/dev/null 2>&1; then bad "$what"; else ok "$what"; fi
}

[[ -r "$CONTRACT" ]] || { echo "contract not found: $CONTRACT" >&2; exit 2; }
for tool in jq yq; do
  command -v "$tool" >/dev/null || { echo "$tool is required" >&2; exit 2; }
done

# ---------------------------------------------------------------- the version file (FR-005a)
note "version"
version_path="$(q .version_file.path)"
version_pattern="$(q .version_file.pattern)"
check "$version_path exists" test -f "$version_path"
if [[ -f "$version_path" ]]; then
  check "$version_path holds one line matching $version_pattern" bash -c \
    "[[ \$(wc -l < '$version_path') -eq 1 ]] && grep -qE '$version_pattern' '$version_path'"
fi
# Nothing may write it: a job or script that sets it would make FR-005a a comment rather than a fact.
refuse "no workflow or script writes $version_path" bash -c \
  "grep -rnE '((>|>>|tee)[[:space:]]*\.?/?$version_path([[:space:]]|\$)|sed -i[^|]*$version_path)' \
     .github scripts 2>/dev/null | grep -q ."

# ---------------------------------------------------------------- the workflows
while read -r wf; do
  path="$(echo "$wf" | jq -r .path)"
  note "${path#.github/workflows/}"

  if [[ ! -f "$path" ]]; then
    bad "$path exists"
    continue
  fi
  ok "$path exists"
  check "$path is valid YAML" yq -e '.' "$path"

  while read -r trigger; do
    check "triggers on $trigger" yq -e ".on | has(\"$trigger\")" "$path"
  done < <(echo "$wf" | jq -r '.triggers[]')

  while read -r branch; do
    check "push is limited to $branch" yq -e \
      ".on.push.branches | contains([\"$branch\"])" "$path"
  done < <(echo "$wf" | jq -r '.push_branches // [] | .[]')

  # An allow-list of what can change an image (FR-004). Here — unlike ci.yml, where research E4
  # rejected one — the failure mode of forgetting an entry is "we did not publish", which is safe
  # and noticed. On ci.yml it would be "we did not check", which is neither.
  while read -r p; do
    check "push is limited to $p" yq -e ".on.push.paths | contains([\"$p\"])" "$path"
  done < <(echo "$wf" | jq -r '.paths // [] | .[]')
  while read -r p; do
    check "push ignores $p" yq -e ".on.push.paths-ignore | contains([\"$p\"])" "$path"
  done < <(echo "$wf" | jq -r '.paths_ignore // [] | .[]')

  # Least privilege, declared in the file rather than in a settings page (FR-007).
  while read -r scope value; do
    check "workflow permissions: $scope is $value" yq -e \
      ".permissions.$scope == \"$value\"" "$path"
  done < <(echo "$wf" | jq -r '.permissions | to_entries[] | "\(.key) \(.value)"')

  cancel="$(echo "$wf" | jq -r '.concurrency.cancel_in_progress')"
  check "runs are serialised by a concurrency group" yq -e '.concurrency.group' "$path"
  check "superseded runs are cancelled: $cancel" yq -e \
    ".concurrency.cancel-in-progress == $cancel" "$path"

  while read -r job; do
    check "job $job is defined" yq -e ".jobs | has(\"$job\")" "$path"
  done < <(echo "$wf" | jq -r '.jobs[]')

  # A write scope, where the contract allows one, belongs to a single job and not the workflow.
  while read -r job scope value; do
    check "job $job holds $scope: $value" yq -e \
      ".jobs.$job.permissions.$scope == \"$value\"" "$path"
  done < <(echo "$wf" | jq -r '.job_permissions // {} | to_entries[] as $j
              | $j.value | to_entries[] | "\($j.key) \(.key) \(.value)"')

  while read -r forbidden; do
    refuse "no $forbidden anywhere in $path" grep -qF "$forbidden" "$path"
  done < <(echo "$wf" | jq -r '.forbidden_permissions // [] | .[]')
done < <(qc '.workflows[]')

# ---------------------------------------------------------------- things no workflow may contain
note "forbidden everywhere"
shopt -s nullglob
workflows=(.github/workflows/*.yml .github/workflows/*.yaml)
shopt -u nullglob
if [[ ${#workflows[@]} -eq 0 ]]; then
  bad "at least one workflow exists under .github/workflows/"
else
  ok "${#workflows[@]} workflow file(s) under .github/workflows/"
  while read -r pattern; do
    refuse "no '$pattern' in any workflow" grep -qF "$pattern" "${workflows[@]}"
  done < <(q '.forbidden_everywhere.patterns[]')
fi

# ---------------------------------------------------------------- action pins (FR-003)
note "action pins"
if [[ ${#workflows[@]} -gt 0 ]]; then
  uses="$(grep -hoP '^\s*(- )?uses:\s*\K\S+' "${workflows[@]}" | sort -u)"
  if [[ -z "$uses" ]]; then
    bad "the workflows use at least one action"
  else
    while read -r ref; do
      [[ -z "$ref" ]] && continue
      # A local action (./.github/actions/...) is this repository's own code and needs no pin.
      [[ "$ref" == ./* ]] && continue
      if [[ "$ref" =~ @[0-9a-f]{40}$ ]]; then
        ok "${ref%%@*} is pinned to a commit"
      else
        bad "${ref%%@*} is not pinned to a 40-character SHA (FR-003): $ref"
      fi
    done <<< "$uses"


  fi
fi

# ---------------------------------------------------------------- what is published (FR-005)
note "images"
release=".github/workflows/release.yml"
if [[ -f "$release" ]]; then
  registry="$(q .images.registry)"
  owner="$(q .images.owner_from)"
  check "the registry is $registry" grep -qF "$registry" "$release"
  # Never a hardcoded owner: a fork publishes into its own namespace, not the original's.
  check "the owner comes from $owner" grep -qF "$owner" "$release"
  while read -r service; do
    check "$service is published" grep -qF "$service" "$release"
  done < <(q '.images.services[]')
  # In the tags: block, not in a comment about it.
  check "images are tagged with the contents of $version_path" yq -e \
    '[.jobs.publish.steps[] | select(.id == "meta") | .with.tags] | join(" ") | test("type=raw")' \
    "$release"
  # In whichever job holds it — it moved from `publish` to `preflight` when the existence check
  # was pulled out of the matrix.
  check "the version is read from $version_path" yq -e \
    "[.jobs[].steps[] | select(.id == \"version\") | .run] | join(\" \") | test(\"$version_path\")" \
    "$release"
  check "images are tagged with the commit" yq -e \
    '[.jobs.publish.steps[] | select(.id == "meta") | .with.tags] | join(" ") | test("type=sha")' \
    "$release"
fi

# ---------------------------------------------------------------- the scanners (FR-010, FR-011, FR-013)
note "scanners"
scan="$(q .scan_script.path)"
check "$scan exists and is executable" test -x "$scan"
if [[ -x "$scan" ]]; then
  # `set -e` would stop at the first finding and hide the other seven.
  refuse "$scan does not abort on the first finding" grep -qE '^set -[a-z]*e[a-z]*o?' "$scan"
  # Match an invocation at the start of a line, not the banner that announces it: `grep -F "trivy"`
  # is satisfied by the `say "trivy — ..."` line alone, which is a check that cannot fail.
  while read -r name; do
    bin="${name%% *}"
    check "$scan actually invokes $bin" grep -qE "^[[:space:]]*(\(cd [^)]*&& )?$bin " "$scan"
  done < <(q '.scanners[].name')
fi

# ---------------------------------------------------------------- dependency updates (FR-008, FR-009)
note "renovate"
renovate="$(q .renovate.path)"
check "$renovate exists" test -f "$renovate"
if [[ -f "$renovate" ]]; then
  check "$renovate is valid JSON" jq -e . "$renovate"
  while read -r manager; do
    check "manager $manager is configured" jq -e --arg m "$manager" "has(\$m)" "$renovate"
  done < <(q '.renovate.managers[]')
  check "digests stay pinned across updates" jq -e '.pinDigests == true' "$renovate"
  # `.automerge? // empty` drops `false` as well as absent — jq's // treats false as empty — so the
  # obvious spelling produces an empty array and passes on a config that never mentions automerge.
  # Ask instead: does any automerge-ish key anywhere have a truthy value?
  refuse "nothing merges itself" jq -e \
    '[.. | objects | to_entries[] | select(.key | test("^(automerge|platformAutomerge)$")) | .value]
     | any(. == true)' "$renovate"
  check "automerge is stated, not merely absent" jq -e '.automerge == false' "$renovate"
  while read -r key; do
    refuse "no deprecated key '$key' (gotcha #7)" grep -qF "\"$key\"" "$renovate"
  done < <(q '.renovate.forbidden_keys[]')
fi

# ---------------------------------------------------------------- triage (FR-012)
note "findings"
findings="$(q .findings_document.path)"
check "$findings exists" test -f "$findings"
if [[ -f "$findings" ]]; then
  while read -r column; do
    check "the table has a '$column' column" grep -qE "^\|.*\b$column\b.*\|" "$findings"
  done < <(q '.findings_document.columns[]')
  while read -r decision; do
    check "the document defines the decision '$decision'" grep -qF "$decision" "$findings"
  done < <(q '.findings_document.decisions[]')
fi

# ----------------------------------------------------------------
printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
