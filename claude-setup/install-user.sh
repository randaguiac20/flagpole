#!/usr/bin/env bash
# Installs the user-scope examples into ~/.claude/ without overwriting anything that already exists.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
mkdir -p "$HOME/.claude/rules"
copy() { if [[ -e "$2" ]]; then echo "keep   $2 (exists)"; else cp "$1" "$2"; echo "create $2"; fi; }
copy "$HERE/user/CLAUDE.md" "$HOME/.claude/CLAUDE.md"
copy "$HERE/user/rules-shell-style.md" "$HOME/.claude/rules/shell-style.md"
echo "Verify with /memory or /context in a new session. Remove with: rm ~/.claude/CLAUDE.md ~/.claude/rules/shell-style.md"
