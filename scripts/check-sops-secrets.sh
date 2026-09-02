#!/usr/bin/env bash
# pre-commit + CI check: every `kind: Secret` under deploy/ or clusters/ must carry a sops: envelope with ENC[ values.
# Same rule as the secret-guard hook, applied to files on disk (catches edits made outside Claude Code).
set -euo pipefail
rc=0
files=("$@")
[[ ${#files[@]} -eq 0 ]] && mapfile -t files < <(git ls-files 'deploy/**/*.yaml' 'deploy/**/*.yml' 'clusters/**/*.yaml' 'clusters/**/*.yml' 2>/dev/null)
for f in "${files[@]}"; do
  [[ -f "$f" ]] || continue
  bad="$(python3 - "$f" <<'PY'
import re, sys
docs = re.split(r"^---\s*$", open(sys.argv[1], encoding="utf-8").read(), flags=re.M)
out = [str(i+1) for i, d in enumerate(docs)
       if re.search(r"^kind:\s*Secret\s*$", d, re.M) and re.search(r"^(data|stringData):", d, re.M)
       and not (re.search(r"^sops:", d, re.M) and "ENC[" in d)]
print(",".join(out))
PY
)"
  if [[ -n "$bad" ]]; then echo "PLAINTEXT SECRET: $f (document $bad) — encrypt with: sops --encrypt --in-place $f" >&2; rc=1; fi
done
exit $rc
