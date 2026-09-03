#!/usr/bin/env bash
# Asserts docs/TUTORIAL.md against the repository. Chore, no spec.
#
# A tutorial is almost entirely commands and paths, which makes it the fastest document in a
# repository to rot and the slowest to notice: it is read by newcomers, who assume the mistake is
# theirs. This repository has already shipped `make e2e TARGET=cluster` in three separate files
# without that target ever existing (gotcha #50). So every make target, script, file, skill, agent
# and MCP server the tutorial names is extracted from the document itself and checked to exist.
#
# It deliberately does NOT run the lessons. It checks that what the document points at is real,
# which is the failure mode that actually happens; whether the output still matches is what
# `make test`, `make test-hooks` and the e2e suite are for.
#
# Prove it still bites before trusting it:
#   sed -i 's/make test-hooks/make test-hooks-nope/' docs/TUTORIAL.md && scripts/check-tutorial.sh
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2
DOC="docs/TUTORIAL.md"
pass=0 fail=0

ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail + 1)); }
note() { printf '\n\033[1m%s\033[0m\n' "$1"; }

[[ -r "$DOC" ]] || { echo "$DOC not found" >&2; exit 2; }

# ---------------------------------------------------------------- make targets
note "make targets the tutorial calls"
while read -r target; do
  if grep -qE "^$target:" Makefile; then ok "make $target is defined"
  else bad "make $target is NOT defined in the Makefile"; fi
done < <(grep -ohE '\bmake [a-z][a-z-]+' "$DOC" | awk '{print $2}' | sort -u)

# ---------------------------------------------------------------- scripts
note "scripts the tutorial calls"
while read -r script; do
  if [[ -x "$script" ]]; then ok "$script exists and is executable"
  elif [[ -f "$script" ]]; then bad "$script exists but is not executable"
  else bad "$script does NOT exist"; fi
done < <(grep -ohE '\bscripts/[a-z-]+\.sh' "$DOC" | sort -u)

# ---------------------------------------------------------------- paths
# Every path named in the prose or a command. A token counts as a path only if it carries a file
# extension or ends in a slash: without that rule `consumer/dex` (from the phrase "api/web/consumer/dex")
# and `deploy/traefik` (a kubectl resource, not a directory) are reported as missing files, and a
# checker that cries wolf gets switched off. Globs are matched against the tree.
note "paths the tutorial names"
while read -r path; do
  [[ -n "$path" ]] || continue
  if [[ "$path" == *"*"* ]]; then
    # shellcheck disable=SC2086
    if compgen -G "$path" >/dev/null; then ok "$path matches at least one file"
    else bad "$path matches NOTHING"; fi
  elif [[ -e "$path" ]]; then ok "$path exists"
  else bad "$path does NOT exist"; fi
done < <(grep -ohE '\b(docs|specs|templates|plugins|scripts|backend|frontend|consumer|mcp|deploy|clusters)/[A-Za-z0-9._*/-]+|\.claude/[A-Za-z0-9._*/-]+|\.mcp\.json|CLAUDE\.md|Makefile|\.mise\.toml' "$DOC" \
      | sed 's/[.,)]*$//' | grep -v '_probe\.py' \
      | grep -E '\.(md|sh|json|ya?ml|py|ts|tsx|toml)$|/$|^Makefile$' | sort -u)

# ---------------------------------------------------------------- components
note "skills the tutorial names"
for skill in add-flag-field api-conventions; do
  if [[ -f ".claude/skills/$skill/SKILL.md" ]]; then ok "skill $skill"
  else bad "skill $skill is missing"; fi
done
for skill in deploy-local e2e security-scan; do
  if [[ -f "plugins/flagpole-tools/skills/$skill/SKILL.md" ]]; then ok "plugin skill $skill"
  else bad "plugin skill $skill is missing"; fi
done

note "agents the tutorial names"
for agent in code-reviewer ui-tester; do
  if [[ -f ".claude/agents/$agent.md" ]]; then ok "agent $agent"
  else bad "agent $agent is missing"; fi
done
for agent in security-auditor deploy-verifier; do
  if [[ -f "plugins/flagpole-tools/agents/$agent.md" ]]; then ok "plugin agent $agent"
  else bad "plugin agent $agent is missing"; fi
done

note "MCP servers the tutorial names"
for server in playwright flagpole-mcp; do
  if jq -e --arg s "$server" '.mcpServers[$s]' .mcp.json >/dev/null 2>&1; then ok "mcp $server"
  else bad "mcp $server is not in .mcp.json"; fi
done

# Every bare `*.sh` the document mentions has to resolve somewhere real. Scripts are already
# covered above, so they are skipped rather than double-counted; anything left that is neither a
# hook nor a hook test is a name the tutorial invented.
note "hooks the tutorial names"
while read -r sh; do
  if   [[ -x ".claude/hooks/$sh" ]];       then ok "hook $sh"
  elif [[ -x ".claude/hooks/tests/$sh" ]]; then ok "hook harness $sh"
  elif [[ -f "scripts/$sh" ]];             then continue
  else bad "$sh is not a hook, a hook test, or a script"; fi
done < <(grep -ohE '\b[a-z][a-z-]*\.sh' "$DOC" | sort -u)

# ---------------------------------------------------------------- claims with numbers
# The two counts the tutorial quotes as output. They drift the moment anyone adds a row or a test,
# and a tutorial quoting the wrong number is how a reader concludes their setup is broken.
note "numbers the tutorial quotes"
rows=$(grep -cE '^\| [0-9]+ \|' docs/gotchas.md)
if grep -q "gotchas.md\` — $rows rows" "$DOC"; then ok "gotcha count ($rows) matches docs/gotchas.md"
else bad "the tutorial's gotcha count does not match docs/gotchas.md ($rows rows)"; fi

claude_md=$(wc -l < CLAUDE.md)
if grep -qE "# $claude_md\$|\| $claude_md \|" "$DOC" || grep -q "wc -l CLAUDE.md          # $claude_md" "$DOC"; then
  ok "CLAUDE.md line count ($claude_md) matches"
else bad "the tutorial quotes a CLAUDE.md line count that is not $claude_md"; fi

# ---------------------------------------------------------------- internal links
# Build the anchor list the way the renderer does — lowercase, drop anything that is not a letter,
# digit, space or hyphen, then spaces to hyphens — and compare. Matching in the other direction
# (turning an anchor back into a regex) cannot handle "Appendix A — trusting", where the em dash
# vanishes and leaves the two hyphens that surrounded it.
note "internal anchors"
mapfile -t anchors < <(grep -E '^#+ ' "$DOC" | sed -E 's/^#+ +//' \
  | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9 -]//g; s/ /-/g')
while read -r link; do
  if printf '%s\n' "${anchors[@]}" | grep -qxF "${link#\#}"; then ok "anchor $link resolves"
  else bad "anchor $link has no matching heading"; fi
done < <(grep -ohE '\]\(#[a-z0-9-]+\)' "$DOC" | tr -d ']()' | sort -u)

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
