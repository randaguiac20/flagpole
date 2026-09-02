#!/usr/bin/env bash
# Installs the managed-policy examples. Requires root; this script NEVER runs sudo itself.
# It prints the exact commands and asks you to run them (in Claude Code: `! sudo ...`).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname -s)" in
  Linux*)  DIR="/etc/claude-code" ;;
  Darwin*) DIR="/Library/Application Support/ClaudeCode" ;;
  *) echo "Windows: copy claude-setup/managed/* to C:\\Program Files\\ClaudeCode\\ as Administrator"; exit 0 ;;
esac
cat <<MSG
Managed policy files are read from: $DIR
They apply to every user on this machine and cannot be excluded by claudeMdExcludes.

Run these commands yourself (review the files first):

  sudo mkdir -p "$DIR"
  sudo cp "$HERE/managed/CLAUDE.md" "$DIR/CLAUDE.md"
  sudo cp "$HERE/managed/managed-settings.json" "$DIR/managed-settings.json"

Verify in a new session with /context (the file appears under "Memory files" as Managed)
and /doctor. Remove with: sudo rm "$DIR/CLAUDE.md" "$DIR/managed-settings.json"
MSG
