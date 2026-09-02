# Decision: `.claude/settings.json` permissions

- **Problem / trigger**: three commands are catastrophic in this repo (force-push, `kubectl delete`, `rm -rf`) and `sops -d` would put plaintext secrets into Claude's context. An instruction is a request; a rule is enforcement.
- **Alternative rejected**: a CLAUDE.md "never" line (not guaranteed); a `PreToolUse` hook for these (needs no argument inspection beyond a prefix, so the cheaper mechanism wins, docs: "use the permission system rather than a hook to enforce a hard allow or deny").
- **Limits**: allow list = only this repo's workflow commands (read-only kubectl/flux, build, test, git status/add/commit) + `mcp__playwright__*`; deny = 16 rules; ask = pushes, bootstrap, cluster create, GitHub mutations. No `bypassPermissions`, no `defaultMode` override (user chooses the mode).
- **Not done**: no `additionalDirectories`, no sandbox config, no `disableAllHooks`. Signal: a prompt that appears more than twice per session for a safe read-only command → add it to `allow`.
- **Verification**: `kubectl delete namespace probe-does-not-exist` → "Permission to use Bash ... has been denied" (2026-09-02, see walkthrough). `/permissions` lists the rules.
