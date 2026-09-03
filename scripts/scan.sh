#!/usr/bin/env bash
# Every scanner, in one command, locally and in CI. Spec: 006-ci-and-security FR-010, FR-011,
# FR-012, FR-013 (T005, T008).
#
# Three things make this more than a list of commands:
#   1. It does NOT `set -e`. Eight scanners behind `set -e` means the first finding hides the other
#      seven, and you get one run per fix instead of one fix per run.
#   2. A tool that is not installed is a FAILURE, not a skip (FR-011). A scanner that reports
#      nothing because it never ran is worse than no scanner: it reports "clean".
#   3. A finding at or above its threshold fails the run until it has a row in
#      docs/security-findings.md with a decision, a reason and a date (FR-012). That document is the
#      only way past a scanner, which is what stops it becoming a list nobody reads.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2

FINDINGS="docs/security-findings.md"
OUT="${FLAGPOLE_SCAN_DIR:-$ROOT/.scan}"
rm -rf "$OUT"; mkdir -p "$OUT"

say()  { printf '\n\033[1m== %s\033[0m\n' "$1"; }
info() { printf '   %s\n' "$1"; }

names=() states=() counts=()

# The tracked tree: exactly the files this repository contains, with their working-tree content.
# gitleaks' `dir` and `trivy fs` both walk everything on disk, including gitignored paths — which
# means a developer's local dev key is reported as a finding in the repository. Copying the tracked
# files aside is scoping, not suppression: nothing is excluded from what is actually committed.
TRACKED="$OUT/tracked"
mkdir -p "$TRACKED"
git ls-files -z | xargs -0 -r cp --parents -t "$TRACKED" 2>/dev/null

record() { names+=("$1"); states+=("$2"); counts+=("$3"); }

# ids_above <scanner> — the identifiers this scanner reported at or above its threshold, one per
# line, written by each scanner into $OUT/<scanner>.ids.
have() { command -v "$1" >/dev/null 2>&1; }

missing() { # missing <scanner> <install hint>
  printf '   \033[31mNOT INSTALLED\033[0m — %s\n' "$2"
  record "$1" missing 0
}

wrote_json() { # wrote_json <file>... — every file must exist and parse
  local f
  for f in "$@"; do
    [[ -s "$f" ]] || { printf '   \033[31mNO OUTPUT\033[0m — %s\n' "$f"; return 1; }
    jq -e . "$f" >/dev/null 2>&1 || {
      printf '   \033[31mNOT JSON\033[0m — %s said:\n' "$f"
      sed 's/^/     /' "${f%.json}.err" 2>/dev/null | head -3
      return 1
    }
  done
}

broke() { # broke <scanner> — it ran but produced nothing usable (FR-011)
  printf '   \033[31mERRORED\033[0m — its output did not parse; treating as a failure\n'
  record "$1" errored 0
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

# ---------------------------------------------------------------- python dependencies
say "pip-audit — python dependencies (any known vulnerability)"
if ! have pip-audit; then
  missing pip-audit "uv tool install pip-audit"
else
  : > "$OUT/pip-audit.ids"
  for svc in backend consumer mcp/flagpole-mcp; do
    [[ -f "$svc/pyproject.toml" ]] || continue
    info "$svc"
    (cd "$svc" && uv export --no-emit-project --format requirements.txt 2>/dev/null) \
      > "$OUT/req-${svc//\//-}.txt"
    pip-audit --requirement "$OUT/req-${svc//\//-}.txt" --format json --progress-spinner off \
      > "$OUT/pip-audit-${svc//\//-}.json" 2>"$OUT/pip-audit-${svc//\//-}.err"
    jq -r '.dependencies[]? | .vulns[]? | .id' "$OUT/pip-audit-${svc//\//-}.json" \
      2>/dev/null >> "$OUT/pip-audit.ids"
  done
  finish pip-audit
fi

# ---------------------------------------------------------------- npm dependencies
say "npm audit — npm dependencies (high and critical)"
if ! have npm; then
  missing "npm audit" "install node"
else
  (cd frontend && npm audit --json) > "$OUT/npm-audit.json" 2>"$OUT/npm-audit.err"
  jq -r '.vulnerabilities[]? | select(.severity == "high" or .severity == "critical")
         | (.via[]? | objects | .url // .source | tostring), .name' \
    "$OUT/npm-audit.json" 2>/dev/null | grep -oE 'GHSA-[a-z0-9-]+|^[a-z0-9@/._-]+$' \
    > "$OUT/npm-audit.ids"
  finish npm-audit
fi

# ---------------------------------------------------------------- every lockfile
say "osv-scanner — every lockfile (CVSS >= 7.0)"
if ! have osv-scanner; then
  missing osv-scanner "mise use -g osv-scanner"
else
  osv-scanner scan source -r --format json . > "$OUT/osv.json" 2>"$OUT/osv.err"
  jq -r '.results[]?.packages[]?.groups[]?
         | select((.max_severity // "0") != "" and ((.max_severity // "0") | tonumber) >= 7.0)
         | .ids[]' "$OUT/osv.json" 2>/dev/null > "$OUT/osv-scanner.ids"
  finish osv-scanner
fi

# ---------------------------------------------------------------- images and manifests
say "trivy — filesystem and Kubernetes manifests (HIGH and CRITICAL)"
if ! have trivy; then
  missing trivy "mise use -g trivy"
else
  trivy fs --quiet --scanners vuln,secret,misconfig --severity HIGH,CRITICAL \
    --format json "$TRACKED" > "$OUT/trivy-fs.json" 2>"$OUT/trivy-fs.err"
  # One directory per invocation: `trivy config` takes a single DIR and exits FATAL on two, which
  # produced an empty report that jq turned into "clean" the first time this was run.
  outputs=("$OUT/trivy-fs.json")
  for dir in deploy platform clusters; do
    trivy config --quiet --severity HIGH,CRITICAL --format json \
      "$dir" > "$OUT/trivy-config-$dir.json" 2>"$OUT/trivy-config-$dir.err"
    outputs+=("$OUT/trivy-config-$dir.json")
  done
  if wrote_json "${outputs[@]}"; then
    jq -r '.Results[]? | (.Vulnerabilities[]?.VulnerabilityID),
           (.Misconfigurations[]?.ID), (.Secrets[]?.RuleID)' \
      "${outputs[@]}" 2>/dev/null > "$OUT/trivy.ids"
    finish trivy
  else
    broke trivy
  fi
fi

# ---------------------------------------------------------------- Dockerfiles
say "hadolint — the three Dockerfiles (error)"
if ! have hadolint; then
  missing hadolint "mise use -g hadolint"
else
  hadolint --format json backend/Dockerfile consumer/Dockerfile frontend/Dockerfile \
    > "$OUT/hadolint.json" 2>"$OUT/hadolint.err"
  jq -r '.[]? | select(.level == "error") | .code' "$OUT/hadolint.json" \
    2>/dev/null > "$OUT/hadolint.ids"
  finish hadolint
fi

# ---------------------------------------------------------------- secrets
say "gitleaks — secrets in the tree and its history (any finding)"
if ! have gitleaks; then
  missing gitleaks "mise use -g gitleaks"
else
  : > "$OUT/gitleaks.ids"
  gitleaks git . --no-banner --redact --report-format json \
    --report-path "$OUT/gitleaks-git.json" >"$OUT/gitleaks.log" 2>&1
  gitleaks dir "$TRACKED" --no-banner --redact --report-format json \
    --report-path "$OUT/gitleaks-dir.json" >>"$OUT/gitleaks.log" 2>&1
  # Report the repository's path, not the path inside the scanned copy.
  jq -r '.[]? | "\(.RuleID) \(.File):\(.StartLine)"' \
    "$OUT/gitleaks-git.json" "$OUT/gitleaks-dir.json" 2>/dev/null \
    | sed "s|$TRACKED/||" >> "$OUT/gitleaks.ids"
  finish gitleaks
fi

# ---------------------------------------------------------------- python source
say "bandit — python source (HIGH)"
if ! have bandit; then
  missing bandit "uv tool install bandit"
else
  bandit -r backend/app consumer/app mcp/flagpole-mcp/flagpole_mcp -f json -q \
    > "$OUT/bandit.json" 2>"$OUT/bandit.err"
  jq -r '.results[]? | select(.issue_severity == "HIGH") | "\(.test_id) \(.filename):\(.line_number)"' \
    "$OUT/bandit.json" 2>/dev/null > "$OUT/bandit.ids"
  finish bandit
fi

# ---------------------------------------------------------------- python and typescript source
say "semgrep — python and typescript source (ERROR)"
if ! have semgrep; then
  missing semgrep "uv tool install semgrep"
else
  # Explicit rulesets, never --config auto: auto resolves the rule set at run time and uploads
  # project metadata. The semgrep VERSION is pinned; the ruleset CONTENTS come from the registry and
  # are the one input this repository does not pin — see docs/decisions/security-scanning.md.
  semgrep scan --metrics=off --quiet --json \
    --config p/python --config p/typescript --config p/bash \
    backend consumer frontend/src mcp scripts > "$OUT/semgrep.json" 2>"$OUT/semgrep.err"
  jq -r '.results[]? | select(.extra.severity == "ERROR")
         | "\(.check_id) \(.path):\(.start.line)"' "$OUT/semgrep.json" \
    2>/dev/null > "$OUT/semgrep.ids"
  finish semgrep
fi

# ---------------------------------------------------------------- triage (FR-012)
# A finding is allowed past only when docs/security-findings.md says something about it. The match
# is on the identifier, which is why the document has an Identifier column.
say "triage against $FINDINGS"
unrecorded=0
if [[ ! -f "$FINDINGS" ]]; then
  printf '   \033[31m%s does not exist\033[0m\n' "$FINDINGS"
  unrecorded=1
else
  for f in "$OUT"/*.ids; do
    [[ -s "$f" ]] || continue
    while read -r id _rest; do
      [[ -z "$id" ]] && continue
      if grep -qF "$id" "$FINDINGS"; then
        info "recorded    $id"
      else
        printf '   \033[31mUNRECORDED\033[0m  %s\n' "$id"
        unrecorded=$((unrecorded + 1))
      fi
    done < <(sort -u "$f")
  done
  [[ $unrecorded -eq 0 ]] && info "every finding above its threshold has a row"
fi

# ---------------------------------------------------------------- summary
printf '\n\033[1m%-14s %-10s %s\033[0m\n' SCANNER STATE FINDINGS
rc=0
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
