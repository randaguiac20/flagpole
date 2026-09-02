# Decision: hook `PreToolUse(Bash)` → `gitops-guard.sh`

- **Problem / trigger**: drift. `kubectl apply/scale/rollout restart` into `flagpole-*` namespaces makes the cluster disagree with git and hides the GitOps lesson. Serves spec `005-platform-delivery` (Flux owns the cluster).
- **Alternative rejected**: `permissions.deny` on `Bash(kubectl apply *)`: cannot express "except `-n flux-system`", which bootstrap needs (`sops-age` secret). CLAUDE.md line: a request, not enforcement.
- **Limits**: `matcher: Bash`, `if: "Bash(kubectl *)"`, `timeout: 5`, exec form, no network. Denies via `permissionDecision: deny` (exit 0 + JSON). Fail-closed: unreadable input → exit 2. Read-only verbs pass silently.
- **Not done**: no allow-listing of `helm`/`flux` mutations (they are ask/allow rules). Signal: a `helm install` by hand seen in the log.
- **Verification**: 9 cases in `make test-hooks`; live on 2026-09-02: `kubectl apply -k deploy/overlays/dev` → denied with the reason shown to Claude (`.claude/logs/hooks.log`).
