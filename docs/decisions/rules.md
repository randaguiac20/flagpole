# Decision: `.claude/rules/` (4 files)

- **Problem / trigger**: Python, TypeScript and manifest conventions are long and only matter when touching those trees; loading them always would bloat every prompt. `workflow.md` holds the few always-on process rules that would otherwise crowd CLAUDE.md.
- **Alternative rejected**: one big CLAUDE.md (context cost on every request); nested CLAUDE.md per directory (loads on directory access, not on file type, and cannot span `backend/`+`consumer/`+`mcp/` in one file).
- **Limits**: 3 path-scoped (`python-services`, `frontend`, `kubernetes-manifests`) + 1 unconditional (`workflow`). One topic per file, ≤ 21 lines each, no overlapping globs.
- **Not done**: no `~/.claude/rules` team rules, no symlinked shared rules (single repo). Signal: a second repo wants the same Python rule → symlink or plugin.
- **Verification**: `InstructionsLoaded` hook (enable via `settings.local.json.example`) logs `path_glob_match` when a `.py` file is read; `/context` shows the rule after such a read. Pending: user-run in the walkthrough.
