#!/usr/bin/env bash
# Every scanner, in one command, locally and in CI. Spec: 006-ci-and-security FR-010, FR-011,
# FR-012, FR-013 (T005, T008).
#
# Three things make this more than a list of commands:
#   1. It does NOT `set -e`. Eight scanners behind `set -e` means the first finding hides the other
#      seven, and you get one run per fix instead of one fix per run.
#   2. A scanner that did not really run is a FAILURE, not a skip (FR-011) — whether it is missing
#      from PATH or ran and produced output that does not parse. "No findings" and "no run" must
#      never produce the same result. The first version of this script enforced that for trivy
#      alone and let seven scanners fail open; the code-reviewer agent caught it.
#   3. A finding at or above its threshold fails the run until it has a ROW in
#      docs/security-findings.md carrying one of the four decisions (FR-012). A mention in prose is
#      not a decision, which is why the match is against a table row and not the file.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

FINDINGS="docs/security-findings.md"
OUT="${FLAGPOLE_SCAN_DIR:-$ROOT/.scan}"
rm -rf "$OUT"; mkdir -p "$OUT"

say()  { printf '\n\033[1m== %s\033[0m\n' "$1"; }
info() { printf '   %s\n' "$1"; }
die()  { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 2; }

names=() states=() counts=()
record() { names+=("$1"); states+=("$2"); counts+=("$3"); }

have() { command -v "$1" >/dev/null 2>&1; }

missing() { # missing <scanner> <install hint>
  printf '   \033[31mNOT INSTALLED\033[0m — %s\n' "$2"
  record "$1" missing 0
}

broke() { # broke <scanner> — it ran but produced nothing usable (FR-011)
  printf '   \033[31mERRORED\033[0m — its output did not parse; treating as a failure\n'
  record "$1" errored 0
}

wrote_json() { # wrote_json <file>... — every file must exist and parse
  local f
  for f in "$@"; do
    [[ -s "$f" ]] || { printf '   \033[31mNO OUTPUT\033[0m — %s\n' "${f#"$OUT"/}"; return 1; }
    jq -e . "$f" >/dev/null 2>&1 || {
      printf '   \033[31mNOT JSON\033[0m — %s said:\n' "${f#"$OUT"/}"
      sed 's/^/     /' "${f%.json}.err" 2>/dev/null | head -3
      return 1
    }
  done
}

finish() { # finish <scanner> — count what it flagged and remember it
  local name="$1" n=0
  [[ -s "$OUT/$name.ids" ]] && n="$(sort -u "$OUT/$name.ids" | grep -c . )"
  if [[ "$n" -gt 0 ]]; then
    info "$n finding(s) at or above the threshold"
    sed 's/^/     /' <(sort -u "$OUT/$name.ids")
    record "$name" flagged "$n"
  else
    info "nothing at or above the threshold"
    record "$name" clean 0
  fi
}

# The tracked tree: exactly the files this repository contains, with their working-tree content.
# gitleaks' `dir`, `trivy fs` and `osv-scanner` all walk everything on disk, including gitignored
# paths — which means a developer's .venv and local dev keys are reported as findings in the
# repository, and the local run stops matching the CI run that has neither. Copying the tracked
# files aside is scoping, not suppression: nothing that is committed is excluded.
#
# The copy is checked. An empty $TRACKED would make three scanners report "clean" for the best
# possible reason and the worst possible cause.
TRACKED="$OUT/tracked"
mkdir -p "$TRACKED"
if ! git ls-files -z | xargs -0 -r cp --parents -t "$TRACKED"; then
  die "could not copy the tracked files into $TRACKED — refusing to scan an incomplete tree"
fi
expected="$(git ls-files | wc -l)"
actual="$(find "$TRACKED" -type f | wc -l)"
[[ "$expected" -gt 0 && "$actual" -eq "$expected" ]] \
  || die "tracked tree holds $actual of $expected files — refusing to scan an incomplete tree"
info "scanning $actual tracked files"

# ---------------------------------------------------------------- python dependencies
say "pip-audit — python dependencies (any known vulnerability)"
if ! have pip-audit; then
  missing pip-audit "mise install (see .mise.toml)"
else
  : > "$OUT/pip-audit.ids"; outs=()
  for svc in backend consumer mcp/flagpole-mcp; do
    [[ -f "$svc/pyproject.toml" ]] || continue
    info "$svc"
    slug="${svc//\//-}"
    (cd "$svc" && uv export --no-emit-project --format requirements.txt 2>"$OUT/uv-$slug.err") \
      > "$OUT/req-$slug.txt"
    [[ -s "$OUT/req-$slug.txt" ]] || { info "uv export produced nothing for $svc"; outs+=("$OUT/missing.json"); continue; }
    pip-audit --requirement "$OUT/req-$slug.txt" --format json --progress-spinner off \
      > "$OUT/pip-audit-$slug.json" 2>"$OUT/pip-audit-$slug.err"
    outs+=("$OUT/pip-audit-$slug.json")
  done
  if wrote_json "${outs[@]}"; then
    jq -r '.dependencies[]? | .vulns[]? | .id' "${outs[@]}" 2>/dev/null > "$OUT/pip-audit.ids"
    finish pip-audit
  else
    broke pip-audit
  fi
fi

# ---------------------------------------------------------------- npm dependencies
say "npm audit — npm dependencies (high and critical)"
if ! have npm; then
  missing "npm-audit" "install node (pinned in .mise.toml)"
else
  (cd frontend && npm audit --json) > "$OUT/npm-audit.json" 2>"$OUT/npm-audit.err"
  if wrote_json "$OUT/npm-audit.json"; then
    # The advisory identifier where npm gives one, the package name where it does not. No grep:
    # a character-class filter silently dropped every package name containing a capital letter.
    jq -r '(.vulnerabilities // {}) | to_entries[]
           | select(.value.severity == "high" or .value.severity == "critical")
           | ([.value.via[]? | objects | .url // empty
               | capture("(?<g>GHSA-[a-z0-9-]+)")? | .g // empty]) as $ghsa
           | if ($ghsa | length) > 0 then $ghsa[] else .key end' \
      "$OUT/npm-audit.json" 2>/dev/null > "$OUT/npm-audit.ids"
    finish npm-audit
  else
    broke npm-audit
  fi
fi

# ---------------------------------------------------------------- every lockfile
say "osv-scanner — every lockfile (CVSS >= 7.0, and anything unscored)"
if ! have osv-scanner; then
  missing osv-scanner "mise install (see .mise.toml)"
else
  # Named lockfiles, not a directory walk. Walking the working directory would also cover .venv
  # and node_modules, which do not exist in CI, so the two runs would disagree (FR-013); walking
  # the tracked copy finds nothing at all, because osv-scanner honours the .gitignore it copied
  # along with everything else. Four files, listed, is the version that cannot drift.
  osv_args=()
  for lock in backend/uv.lock consumer/uv.lock mcp/flagpole-mcp/uv.lock frontend/package-lock.json; do
    [[ -f "$lock" ]] || die "$lock is missing — osv-scanner would report clean for it"
    osv_args+=(--lockfile "$lock")
  done
  osv-scanner scan source "${osv_args[@]}" --format json > "$OUT/osv.json" 2>"$OUT/osv.err"
  if wrote_json "$OUT/osv.json"; then
    # An advisory with no published CVSS vector has max_severity "". Reporting it as unscored is
    # the honest handling; dropping it silently is how a HIGH-impact finding disappears.
    jq -r '.results[]?.packages[]?.groups[]?
           | (.max_severity // "") as $s
           | if ($s | test("^[0-9]"))
             then (if ($s | tonumber) >= 7.0 then .ids[] else empty end)
             else (.ids[] + " (unscored)") end' \
      "$OUT/osv.json" 2>/dev/null > "$OUT/osv-scanner.ids"
    finish osv-scanner
  else
    broke osv-scanner
  fi
fi

# ---------------------------------------------------------------- images and manifests
say "trivy — base images, filesystem and Kubernetes manifests (HIGH and CRITICAL)"
if ! have trivy; then
  missing trivy "mise install (see .mise.toml)"
else
  outs=()
  trivy fs --quiet --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
    --format json "$TRACKED" > "$OUT/trivy-fs.json" 2>"$OUT/trivy-fs.err"
  outs+=("$OUT/trivy-fs.json")

  # One directory per invocation: `trivy config` takes a single DIR and exits FATAL on two, which
  # produced an empty report that jq turned into "clean" the first time this was run.
  for dir in deploy platform clusters; do
    trivy config --quiet --severity HIGH,CRITICAL --format json \
      "$dir" > "$OUT/trivy-config-$dir.json" 2>"$OUT/trivy-config-$dir.err"
    outs+=("$OUT/trivy-config-$dir.json")
  done

  # FR-010 says "container images", and neither `fs` nor `config` looks inside one. The base
  # images are what carry an operating system and its packages; every layer this repository adds on
  # top is source, which `fs` already covers. They are named by digest, so this scans the same
  # bytes here and in CI without either having to build anything.
  mapfile -t bases < <(grep -hoP '^(FROM|COPY[[:space:]]+--from=)[[:space:]]*\K\S+' \
    backend/Dockerfile consumer/Dockerfile frontend/Dockerfile | grep '@sha256:' | sort -u)
  for image in "${bases[@]}"; do
    slug="$(printf '%s' "$image" | tr -c 'A-Za-z0-9' '-')"
    info "image $image"
    trivy image --quiet --severity HIGH,CRITICAL --format json \
      "$image" > "$OUT/trivy-image-$slug.json" 2>"$OUT/trivy-image-$slug.err"
    outs+=("$OUT/trivy-image-$slug.json")
  done

  if wrote_json "${outs[@]}"; then
    jq -r '.Results[]? | (.Vulnerabilities[]?.VulnerabilityID),
           (.Misconfigurations[]?.ID), (.Secrets[]?.RuleID)' \
      "${outs[@]}" 2>/dev/null > "$OUT/trivy.ids"
    finish trivy
  else
    broke trivy
  fi
fi

# ---------------------------------------------------------------- Dockerfiles
say "hadolint — the three Dockerfiles (error)"
if ! have hadolint; then
  missing hadolint "mise install (see .mise.toml)"
else
  hadolint --format json backend/Dockerfile consumer/Dockerfile frontend/Dockerfile \
    > "$OUT/hadolint.json" 2>"$OUT/hadolint.err"
  if wrote_json "$OUT/hadolint.json"; then
    jq -r '.[]? | select(.level == "error") | .code' "$OUT/hadolint.json" \
      2>/dev/null > "$OUT/hadolint.ids"
    finish hadolint
  else
    broke hadolint
  fi
fi

# ---------------------------------------------------------------- secrets
say "gitleaks — secrets in the tree and its history (any finding)"
if ! have gitleaks; then
  missing gitleaks "mise install (see .mise.toml)"
else
  gitleaks git . --no-banner --redact --report-format json \
    --report-path "$OUT/gitleaks-git.json" >"$OUT/gitleaks.log" 2>&1
  gitleaks dir "$TRACKED" --no-banner --redact --report-format json \
    --report-path "$OUT/gitleaks-dir.json" >>"$OUT/gitleaks.log" 2>&1
  if wrote_json "$OUT/gitleaks-git.json" "$OUT/gitleaks-dir.json"; then
    # Report the repository's path, not the path inside the scanned copy.
    jq -r '.[]? | "\(.RuleID) \(.File):\(.StartLine)"' \
      "$OUT/gitleaks-git.json" "$OUT/gitleaks-dir.json" 2>/dev/null \
      | sed "s|$TRACKED/||" > "$OUT/gitleaks.ids"
    finish gitleaks
  else
    broke gitleaks
  fi
fi

# ---------------------------------------------------------------- python source
say "bandit — python source (HIGH)"
if ! have bandit; then
  missing bandit "mise install (see .mise.toml)"
else
  # The packages, never the service directories: `-r mcp/flagpole-mcp` descends into its .venv and
  # reports pygments and httpx as this repository's source.
  bandit -r backend/app consumer/app mcp/flagpole-mcp/flagpole_mcp -f json -q \
    > "$OUT/bandit.json" 2>"$OUT/bandit.err"
  if wrote_json "$OUT/bandit.json"; then
    jq -r '.results[]? | select(.issue_severity == "HIGH")
           | "\(.test_id) \(.filename):\(.line_number)"' \
      "$OUT/bandit.json" 2>/dev/null > "$OUT/bandit.ids"
    finish bandit
  else
    broke bandit
  fi
fi

# ---------------------------------------------------------------- python and typescript source
say "semgrep — python and typescript source (ERROR)"
if ! have semgrep; then
  missing semgrep "mise install (see .mise.toml)"
else
  # Explicit rulesets, never --config auto: auto resolves the rule set at run time and uploads
  # project metadata. The semgrep VERSION is pinned in .mise.toml; the ruleset CONTENTS come from
  # the registry and are the one input this repository does not pin — see
  # docs/decisions/security-scanning.md.
  semgrep scan --metrics=off --quiet --json \
    --config p/python --config p/typescript --config p/bash \
    backend consumer frontend/src mcp scripts > "$OUT/semgrep.json" 2>"$OUT/semgrep.err"
  if wrote_json "$OUT/semgrep.json"; then
    jq -r '.results[]? | select(.extra.severity == "ERROR")
           | "\(.check_id) \(.path):\(.start.line)"' "$OUT/semgrep.json" \
      2>/dev/null > "$OUT/semgrep.ids"
    finish semgrep
  else
    broke semgrep
  fi
fi

# ---------------------------------------------------------------- triage (FR-012)
# A finding is allowed past only when docs/security-findings.md carries a TABLE ROW naming it and
# giving it one of the four decisions. Matching the whole file would let a mention in a heading,
# or a longer identifier that happens to contain this one, count as a decision.
say "triage against $FINDINGS"
unrecorded=0
decisions='\| *(fixed|accepted|not applicable|deferred) *\|'
if [[ ! -f "$FINDINGS" ]]; then
  printf '   \033[31m%s does not exist\033[0m\n' "$FINDINGS"
  unrecorded=1
else
  for f in "$OUT"/*.ids; do
    [[ -s "$f" ]] || continue
    while read -r id _rest; do
      [[ -z "$id" ]] && continue
      if grep '^|' "$FINDINGS" | grep -F "$id" | grep -qE "$decisions"; then
        info "recorded    $id"
      else
        printf '   \033[31mUNRECORDED\033[0m  %s\n' "$id"
        unrecorded=$((unrecorded + 1))
      fi
    done < <(sort -u "$f")
  done
  [[ $unrecorded -eq 0 ]] && info "every finding above its threshold has a row with a decision"
fi

# ---------------------------------------------------------------- summary
printf '\n\033[1m%-14s %-10s %s\033[0m\n' SCANNER STATE FINDINGS
rc=0
{
  printf '%-14s %-10s %s\n' SCANNER STATE FINDINGS
  for i in "${!names[@]}"; do
    printf '%-14s %-10s %s\n' "${names[$i]}" "${states[$i]}" "${counts[$i]}"
  done
} > "$OUT/summary.txt"
for i in "${!names[@]}"; do
  case "${states[$i]}" in
    clean)   colour=32 ;;
    flagged) colour=33 ;;
    *)       colour=31; rc=1 ;;
  esac
  printf '%-14s \033[%sm%-10s\033[0m %s\n' "${names[$i]}" "$colour" "${states[$i]}" "${counts[$i]}"
done

if [[ $unrecorded -gt 0 ]]; then
  printf '\n\033[31m%d finding(s) without a row in %s.\033[0m\n' "$unrecorded" "$FINDINGS"
  printf 'Fix them, or record each one with a decision, a reason and a date.\n'
  rc=1
fi
[[ $rc -eq 0 ]] && printf '\n\033[32mall scanners ran; nothing unaccounted for\033[0m\n'
printf 'raw output: %s\n' "${OUT#"$ROOT"/}"
exit $rc
