#!/usr/bin/env bash
# Everything a fresh clone needs before `make dev`, `make test` or `make e2e` will run.
# Entry point for docs/TUTORIAL.md lesson 0.
#
# Two rules this script keeps, both of them the repository's rules rather than this script's:
#
#   - It never runs sudo. Nothing here needs it; if something did, the command would be printed
#     for you to run, the way scripts/cluster-up.sh prints the /etc/hosts line.
#   - The age private key is created OUTSIDE the working tree, because a key inside a repository
#     is one `git add -A` away from being published. See docs/secrets-sops.md.
#
# Idempotent: run it as often as you like. Everything it does is a no-op the second time.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

say()  { printf '\n\033[1m%s\033[0m\n' "$1"; }
ok()   { printf '  \033[32m✓\033[0m %s\n' "$1"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$1"; }
die()  { printf '\n\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

# ---------------------------------------------------------------- tools
# Every missing tool is reported before exiting. Stopping at the first one means one run per
# install, which is the shape gotcha #36 is about: run every check, fail once, with the whole list.
say "tools"
missing=()
for tool in git jq uv node npm docker; do
  if command -v "$tool" >/dev/null 2>&1; then
    ok "$tool"
  else
    warn "$tool — MISSING"
    missing+=("$tool")
  fi
done
if [[ ${#missing[@]} -gt 0 ]]; then
  die "install these first: ${missing[*]}
Versions are pinned in .mise.toml — 'mise install' fetches the whole set."
fi

# Not required to develop, but named here so the gap is visible now rather than at 'make cluster-up'.
say "tools for the cluster (make cluster-up only)"
for tool in k3d kubectl flux sops age-keygen helm; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool"; else warn "$tool — not installed"; fi
done

# ---------------------------------------------------------------- .env
say "configuration"
if [[ -f .env ]]; then
  ok ".env exists — leaving it alone"
else
  cp .env.example .env
  ok ".env created from .env.example (gitignored; every value is a local non-secret default)"
fi
scripts/ports.sh table 2>/dev/null || warn "could not read the port table"

# ---------------------------------------------------------------- dependencies
say "python dependencies"
for d in backend consumer mcp/flagpole-mcp; do
  [[ -f "$d/pyproject.toml" ]] || { warn "$d has no pyproject.toml — skipped"; continue; }
  if (cd "$d" && uv sync --quiet); then ok "$d"; else die "uv sync failed in $d"; fi
done

say "node dependencies"
if [[ -f frontend/package-lock.json ]]; then
  if (cd frontend && npm ci --silent); then ok "frontend"; else die "npm ci failed in frontend"; fi
else
  die "frontend/package-lock.json is missing — npm ci needs it"
fi

# Playwright ships no browser with the npm package, and `make e2e` is the fourth rung of the
# beginner ladder in docs/TUTORIAL.md. Chromium only, and no --with-deps: that flag needs sudo.
say "playwright browser"
if (cd frontend && npx --no-install playwright install chromium); then
  ok "chromium ready"
else
  warn "could not install the browser — 'make e2e' will fail until: cd frontend && npx playwright install chromium"
fi

# ---------------------------------------------------------------- age key
# Deliberately not in the repository. scripts/cluster-up.sh reads the same path and reuses whatever
# it finds here, so bootstrapping twice never produces a second key.
say "decryption key"
AGE_KEY="${SOPS_AGE_KEY_FILE:-$HOME/.config/sops/age/flagpole.agekey}"
AGE_KEY="${AGE_KEY/#\~/$HOME}"
if [[ -s "$AGE_KEY" ]]; then
  ok "using the existing key at $AGE_KEY"
elif command -v age-keygen >/dev/null 2>&1; then
  mkdir -p "$(dirname "$AGE_KEY")" && chmod 700 "$(dirname "$AGE_KEY")"
  if age-keygen -o "$AGE_KEY" >/dev/null 2>&1; then
    chmod 600 "$AGE_KEY"
    ok "created $AGE_KEY"
    warn "this is the only copy — read docs/secrets-sops.md before you lose it"
  else
    warn "age-keygen failed; the key is only needed for make cluster-up"
  fi
else
  warn "age-keygen not installed — skipped (only make cluster-up needs this)"
fi
if [[ -s "$AGE_KEY" ]]; then
  recipient="$(grep -oE 'age1[a-z0-9]+' "$AGE_KEY" | head -1)"
  if [[ -n "$recipient" ]] && ! grep -q "$recipient" .sops.yaml 2>/dev/null; then
    warn ".sops.yaml does not name this key — the cluster could not decrypt anything."
    warn "That is expected for a fresh key; docs/secrets-sops.md says how to add it."
  fi
fi

# ---------------------------------------------------------------- pre-commit
say "pre-commit"
if command -v pre-commit >/dev/null 2>&1; then
  if pre-commit install >/dev/null 2>&1; then
    ok "git hook installed — gitleaks and the SOPS check now run on every commit"
  else
    warn "pre-commit install failed"
  fi
else
  warn "pre-commit not installed (pipx install pre-commit, or mise install) — commits will not be scanned"
fi

# ---------------------------------------------------------------- done
say "done"
cat <<'MSG'
  docs/TUTORIAL.md         the guided course — start at lesson 0
  make test-hooks          fastest proof the repo works (no network, no cluster)
  make dev                 API :18000, web :18010, consumer :18020, Dex :18030
  make e2e                 Playwright, headless; starts what it needs itself

  Sign in as alice@flagpole.local / flagpole (operator) or bob@flagpole.local (viewer).
MSG
