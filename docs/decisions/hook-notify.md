# Decision: hook `Notification(permission_prompt)` → `notify.sh`

- **Problem / trigger**: long `make build`/`flux` waits while a permission prompt sits unanswered. Pure side effect; no reasoning.
- **Alternative rejected**: `preferredNotifChannel` alone (terminal-bell only, not a desktop toast); an `idle_prompt` hook (nags).
- **Limits**: matcher `permission_prompt` only, `timeout: 5`, returns `terminalSequence` (OSC 777) which Claude Code emits itself (hooks have no `/dev/tty`); `notify-send` only when `DISPLAY`/`WAYLAND_DISPLAY` is set. Cannot block; fail-open.
- **Not done**: no Slack/webhook (network, forbidden by §2.4). Signal: a team channel that must see stuck sessions.
- **Verification**: `make test-hooks` ("emits OSC 777 terminalSequence"). Live: a desktop toast when a prompt waits > 6 s (only in an interactive session). Pending: user observation.
