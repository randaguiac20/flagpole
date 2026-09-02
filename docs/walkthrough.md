# Walkthrough — every component fired once, with real output

Entries are added as each phase lands. "Pending" items are run interactively by the maintainer and pasted here.

## Phase 2 — scaffolding (2026-09-02)

### Hook tests (`make test-hooks`)

```
gitops-guard.sh   9 cases ok · secret-guard.sh 8 cases ok · format.sh 3 · stop-tests.sh 5 · notify.sh 1 · session-start.sh 1 · instructions-loaded.sh 2
hook tests: 29 passed, 0 failed
```

### Live in the authoring session (settings reload without restart)

| Probe | Result | Log line (`.claude/logs/hooks.log`) |
|---|---|---|
| Bash `kubectl apply -k deploy/overlays/dev` | denied before running: `gitops-guard: 'kubectl apply' outside flux-system is denied. Flux owns this cluster…` | `gitops-guard deny: kubectl apply -k deploy/overlays/dev` |
| Bash `kubectl delete namespace probe-does-not-exist` | `Permission to use Bash with command kubectl delete namespace probe-does-not-exist has been denied.` (permission rule, no hook involved) | — |
| Write `deploy/base/probe-secret.yaml` with `stringData` | denied: `secret-guard: deploy/base/probe-secret.yaml contains a kind: Secret with plaintext data/stringData (document 1)…`; file never created | `secret-guard deny deploy/base/probe-secret.yaml (document(s) 1)` |
| Edit / Write of a `.py` file | harness message: `PostToolUse hook modified … (likely a formatter)`; file reformatted by ruff | `format ruff format .claude/logs/probe_format.py` |
| First attempt with `if: "Edit(deploy/**)"` only | Write went through, nothing logged → gotcha #5 | — |

### Pending (run in a fresh session, paste output here)

- `/context` — memory files, rules, skills, agents, MCP tools with token counts
- `/hooks` — six events registered from `.claude/settings.json`
- `/mcp` — `playwright` connected from project scope (approve on first run)
- `/agents` — four project agents
- `/memory` — CLAUDE.md, CLAUDE.local.md (after copying the example), auto-memory entry `flagpole-confirmed-decisions`
- `InstructionsLoaded`: copy the hook block from `.claude/settings.local.json.example`, start a session, read `backend/…py` after Phase 3, show `path_glob_match` in `.claude/logs/instructions-loaded.log`
- SessionStart: the "Session facts" reminder at the top of a new session
- `/speckit-constitution` re-run: reports no changes (constitution v1.0.0 already written)
