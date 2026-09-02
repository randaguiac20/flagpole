#!/usr/bin/env bash
# Notification(permission_prompt): desktop alert. Side effect only; cannot block. Fail-open.
# terminalSequence (OSC 777) is emitted by Claude Code itself (hooks have no /dev/tty); notify-send is a bonus when a
# desktop session exists.
set -uo pipefail
source "$(dirname "$0")/lib.sh"
read_input
title="Claude Code · flagpole"
body="$(jget .message)"; body="${body:-Needs your attention}"
if command -v notify-send >/dev/null 2>&1 && [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
  timeout 2 notify-send "$title" "$body" >/dev/null 2>&1 || true
fi
log "$(jget .notification_type): $body"
seq="$(printf '\033]777;notify;%s;%s\007' "$title" "$body")"
jq -nc --arg seq "$seq" '{terminalSequence:$seq}'
