#!/usr/bin/env bash
# Asserts docs/BLUEPRINT.md against the repository. Phase 6 (chore, no spec).
#
# A rebuild document is the easiest thing in a repository to let rot: nothing breaks when it goes
# stale, because nobody runs it until the day they need it. This checks the parts that can be
# checked without an empty machine — the tools it names, the paths it says to create, and the make
# targets it calls — so the parts that CANNOT be checked (creating a GitHub repository, bootstrapping
# the reconciler, installing an app) are the only ones taken on trust, and they are named as such.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 2
DOC="docs/BLUEPRINT.md"
pass=0 fail=0

# --repo-only skips the checks that are about THIS MACHINE (is docker installed, does the pinned
# toolchain resolve) and keeps the ones about the repository. CI uses it: the `claude` CLI is not
# installable on a runner, and failing there would report a defect that does not exist.
REPO_ONLY=0
[[ "${1:-}" == "--repo-only" ]] && REPO_ONLY=1

ok()   { printf '  \033[32mPASS\033[0m %s\n' "$1"; pass=$((pass + 1)); }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=$((fail + 1)); }
note() { printf '\n\033[1m%s\033[0m\n' "$1"; }

[[ -r "$DOC" ]] || { echo "$DOC not found" >&2; exit 2; }

if [[ $REPO_ONLY -eq 0 ]]; then
note "tools the blueprint tells you to have"
for tool in docker mise uv node npm gh git jq claude; do
  if command -v "$tool" >/dev/null 2>&1; then ok "$tool is installed"; else bad "$tool is not installed"; fi
done

note "tools pinned in .mise.toml"
while read -r tool; do
  if mise exec -- "$tool" --version >/dev/null 2>&1; then ok "$tool resolves at its pinned version"
  else bad "$tool does not resolve — run 'mise install'"; fi
done < <(mise exec -- yq -r '.tools | keys | .[]' .mise.toml 2>/dev/null | sed 's/^pipx://; s/^npm://')
else
  note "machine checks skipped (--repo-only)"
fi

note "make targets the blueprint calls"
while read -r target; do
  if grep -qE "^$target:" Makefile; then ok "make $target is defined"
  else bad "make $target is called by the blueprint but not defined in the Makefile"; fi
done < <(grep -oE '\bmake [a-z0-9-]+' "$DOC" | awk '{print $2}' | sort -u)

note "scripts the blueprint calls"
while read -r script; do
  if [[ -x "$script" ]]; then ok "$script exists and is executable"
  else bad "$script is named by the blueprint but is missing or not executable"; fi
done < <(grep -oE '\bscripts/[a-z0-9-]+\.sh' "$DOC" | sort -u)

note "paths the blueprint says the build produces"
for path in \
  CLAUDE.md docs/architecture.md CLAUDE.local.md.example Makefile .env.example .mcp.json \
  .claude/settings.json .claude/rules .claude/hooks .claude/hooks/lib.sh .claude/hooks/tests/run.sh \
  .claude/agents .claude/skills .specify .specify/memory/constitution.md \
  plugins/flagpole-tools/.claude-plugin/plugin.json .claude-plugin/marketplace.json \
  templates templates/PROMPT.md .mise.toml renovate.json VERSION \
  .github/workflows/ci.yml .github/workflows/release.yml \
  docs/security-findings.md docs/renovate.md docs/walkthrough.md docs/gotchas.md docs/anti-patterns.md
do
  if [[ -e "$path" ]]; then ok "$path exists"; else bad "$path is promised by the blueprint and missing"; fi
done

note "every feature the blueprint walks through has its spec artefacts"
while read -r feature; do
  for artefact in spec.md plan.md tasks.md; do
    if [[ -f "specs/$feature/$artefact" ]]; then ok "specs/$feature/$artefact"
    else bad "specs/$feature/$artefact is missing"; fi
  done
done < <(grep -oE '\b00[1-9]-[a-z-]+' "$DOC" | sort -u)

note "the plugin the blueprint builds"
if jq -e '.name == "flagpole-tools"' plugins/flagpole-tools/.claude-plugin/plugin.json >/dev/null 2>&1
then ok "the manifest names flagpole-tools"; else bad "plugin.json does not name flagpole-tools"; fi
for component in skills/deploy-local/SKILL.md skills/security-scan/SKILL.md skills/e2e/SKILL.md \
                 agents/deploy-verifier.md agents/security-auditor.md; do
  if [[ -f "plugins/flagpole-tools/$component" ]]; then ok "plugin holds $component"
  else bad "plugin is missing $component"; fi
done
# Moved, not copied: the same component must not still be in .claude/.
for stale in .claude/skills/deploy-local .claude/skills/security-scan .claude/skills/e2e \
             .claude/agents/deploy-verifier.md .claude/agents/security-auditor.md; do
  if [[ -e "$stale" ]]; then bad "$stale still exists — the plugin was copied, not moved"
  else ok "$stale is gone (moved, not copied)"; fi
done

note "what this script cannot check"
printf '  %s\n' \
  "creating the GitHub repository (gh repo create)" \
  "flux bootstrap github — writes to the remote and stores a token in the cluster" \
  "installing the Mend Renovate app — a GitHub account action" \
  "the cluster itself — scripts/verify-cluster.sh covers that separately"

printf '\n\033[1m%d passed, %d failed\033[0m\n' "$pass" "$fail"
[[ $fail -eq 0 ]]
