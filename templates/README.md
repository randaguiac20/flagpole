# templates

Copy-ready, de-Flagpoled versions of every Claude Code mechanism this repository uses. Each file is
the *shape* plus the one comment that matters: **when to reach for it, and when not to.**

Nothing here is imported by the running project — Flagpole's real components live in `.claude/` and
`plugins/`. These are for starting a repository like this one.

| File | Mechanism | Reach for it when | Do not, when |
|---|---|---|---|
| `CLAUDE.md` | project memory | facts every session needs: commands, layout, names | it is a rule about *some* files, or a procedure |
| `rules/path-scoped.md` | rule | conventions that apply only to files under a path | it applies to everything — that is CLAUDE.md |
| `settings.json` | permissions + hook registration | a command should be blocked or pre-approved by its *shape* | the decision needs the file's content — that is a hook |
| `hooks/lib.sh` | shared hook helpers | you have more than one hook | you have one |
| `hooks/content-guard.sh` | `PreToolUse` hook | the decision needs the content a tool is about to write | a glob would do — use `permissions.deny` |
| `hooks/format-on-write.sh` | `PostToolUse` hook | a deterministic fixup after every edit | it can fail and should stop the turn |
| `agents/reviewer.md` | subagent | a side task reads many files, or must not edit | the user wants to watch it happen |
| `skills/example-procedure/SKILL.md` | skill | you have pasted the same playbook three times | it is a single command — that is a Makefile target |
| `plugin/` | plugin + marketplace | the same components are wanted in **more than one repository** | there is one repository |
| `.mcp.json` | MCP servers | Claude needs data or actions a shell cannot reach | a CLI already returns it |
| `PROMPT.md` | the brief | starting a project like this one | — |

Every placeholder is written `<LIKE THIS>`. Nothing here will work until they are replaced.

Two rules that survive de-Flagpoling, because they are what the walkthrough kept proving:

1. **A check that has never failed has not been tested.** Break it on purpose, watch it go red, put it back.
2. **Enforcement does not belong anywhere it can be switched off** — not in a plugin, not in prose.
