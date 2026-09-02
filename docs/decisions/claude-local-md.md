# Decision: `CLAUDE.local.md.example`

- **Problem / trigger**: personal overrides (cluster name, port shifts, test users) must not leak into team files. The example shows the scope without shipping anyone's data.
- **Alternative rejected**: `.claude/settings.local.json` (it is for permissions/hooks, not prose); a personal section in CLAUDE.md (everyone would inherit it).
- **Limits**: example file only; the real `CLAUDE.local.md` is gitignored. Documents the worktree caveat and the `@~/...` import alternative.
- **Not done**: nothing enforces that local overrides do not contradict team rules. Signal: a conflict actually seen in `/doctor` output.
- **Verification**: `cp CLAUDE.local.md.example CLAUDE.local.md`, then `/context` lists it as a Local memory file. Pending: user-run.
