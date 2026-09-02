# Decision: hook `SessionStart` → `session-start.sh`

- **Problem / trigger**: branch, active spec, whether the k3d cluster is up, Flux readiness, whether the age key exists, and which dev ports are free change between sessions. A CLAUDE.md line was not sufficient because these facts are dynamic.
- **Alternative rejected**: asking Claude to run `git status`/`k3d cluster list` at the start of each session (not guaranteed, costs a turn); `UserPromptSubmit` (would run every prompt).
- **Limits**: matcher `startup|resume` (not `clear`/`compact`), exec form, `timeout: 10`, every probe wrapped in `timeout 3–4`, output ≤ 6 lines via `additionalContext`, never reads the key file content. Fail-open.
- **Not done**: no `CLAUDE_ENV_FILE` exports, no `sessionTitle`. Signal: a script that needs an env var Claude keeps forgetting to set.
- **Verification**: `make test-hooks` case "startup context has branch and key state"; in a fresh session the first system reminder shows "Session facts". Pending: user-run.
