# Settings and permissions

Source: https://code.claude.com/docs/en/settings · https://code.claude.com/docs/en/permissions · https://code.claude.com/docs/en/permission-modes

## Where settings live, and precedence (highest first)

1. Managed (`managed-settings.json`, MDM, claude.ai console) — cannot be overridden
2. CLI flags (`--settings`, `--allowedTools`, `--disallowedTools`)
3. `.claude/settings.local.json` (personal, gitignored by default)
4. `.claude/settings.json` (shared, committed) ← this repo's file
5. `~/.claude/settings.json` (user)

Arrays like `permissions.deny` merge across layers; scalar keys take the highest layer's value. Claude Code watches the files and reloads most changes live (we relied on that: hooks fired in the same session that wrote them).

## Permission rule syntax (the parts we use)

- `Bash(git push *)` prefix with trailing wildcard (`:*` is equivalent); `*` can sit anywhere: `Bash(git push * --force*)`. Leading `VAR=` assignments are stripped before matching for known-safe vars only.
- `Read(path)` / `Edit(path)`: `path` relative to the settings file's directory; `//abs`, `~/home`, `**` any depth. Deny/ask rules match a bare directory name at any depth; allow rules only at the anchored location. **Only `Read` and `Edit` rules are consulted for file tools** (a `Write(...)` permission rule is accepted but ignored; Edit rules cover Write).
- `mcp__server__tool`, `mcp__server__*`, `mcp__server`.
- `Agent(name)` to deny specific subagents.
- Deny wins over ask wins over allow. A bare tool name in `deny` (e.g. `WebFetch`) removes the tool entirely.

Modes: `default` (prompt), `acceptEdits`, `plan`, `auto` (classifier-reviewed), `dontAsk`, `bypassPermissions`. `permissions.defaultMode` sets it; we do not set it in the shared file.

## Enforcement vs guidance (the table that decides where a rule goes)

| Need | Mechanism | Guarantee |
|---|---|---|
| Never run `kubectl delete`, never force-push, never read the age key | `permissions.deny` | absolute, no code |
| Deny only when an argument/content condition holds | `PreToolUse` hook | absolute (exit 2 or `permissionDecision: deny`), needs a script |
| Do X after every edit / at every stop | `PostToolUse` / `Stop` hook | runs every time, cannot reason |
| Prefer X, usually do Y | CLAUDE.md / rule | a request Claude weighs |
| Product/engineering principle checked at plan time | SDD constitution | checked by `/speckit-plan` and `/speckit-analyze` gates |

## Our implementation (`.claude/settings.json`)

- `allow`: the repo workflow only (make/uv/npm/npx/ruff/pytest, read-only git/kubectl/flux, k3d import, docker build, `sops --encrypt`, `mcp__playwright__*`).
- `deny`: force-push variants, `git reset --hard`, `kubectl delete`, `flux uninstall`, `k3d cluster delete`, `rm -rf`, every `sops` decrypt form, `Read` of `*.agekey`, `.env`, `~/.config/sops/age/**`.
- `ask`: `git push`, `flux bootstrap`, `k3d cluster create`, `gh repo`, `gh pr merge`.
- `hooks`: see `hooks.md`. `enabledPlugins`: Phase 6.
- `.claude/settings.local.json.example`: a personal allow rule and the disabled `InstructionsLoaded` hook.

## How to verify

`/permissions` shows the merged rules with their source; a denied command answers `Permission to use Bash with command … has been denied` (seen 2026-09-02 for `kubectl delete namespace …`). `/hooks` shows registered hooks by event.

## Common mistakes

`bypassPermissions` in a shared file; `allow: ["Bash"]`; writing `Write(path)` rules; relying on a CLAUDE.md "never"; forgetting that `settings.local.json` is per checkout and that project allow rules need workspace trust.
