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

### Headless verification (`claude -p --max-turns 1`, fresh session, 2026-09-02 13:13 UTC)

Prompt: "report exactly what is in your context right now …". Answer (abridged, verbatim lines):

```
Ignoring 31 permissions.allow entries from .claude/settings.json: this workspace has not been trusted. …
1. Memory/instruction files: …/CLAUDE.md; docs/architecture.md (imported by CLAUDE.md); …/memory/MEMORY.md (index …)
2. Rule files loaded: .claude/rules/workflow.md only. Path-scoped rules (Python, frontend, manifests) are referenced but not loaded.
3. Skills available: add-flag-field, api-conventions, e2e, speckit-analyze, … speckit-taskstoissues, … Note: /deploy-local and /security-scan are named in CLAUDE.md but are not in my skill list.
4. MCP servers/tools: playwright (deferred tools mcp__playwright__browser_*…). No flagpole-mcp tools are visible.
5. Session facts (verbatim):
Session facts (2026-09-02 startup):
- Branch: main | uncommitted files: 0 | active spec: none (chores on main)
- k3d 'flagpole': cluster 'flagpole' not created (make cluster-up)
- Flux kustomizations: n/a (no cluster)
- SOPS age key: missing (make bootstrap creates it)
- Dev ports: FLAGPOLE_API_PORT:18000(free) FLAGPOLE_WEB_PORT:18010(free) …
```

Reading: (2) confirms path-scoping; (3) confirms `disable-model-invocation: true` hides `/deploy-local` and `/security-scan` from the model; (4) confirms project-scope `.mcp.json` and that `flagpole-mcp` is not registered yet (feature 004); (5) is the SessionStart hook's `additionalContext`. `hooks.log` also shows `notify permission_prompt: Claude needs your permission` from the `git push` approval at 13:11:57 — the Notification hook firing for real.

### Pending (run in a fresh interactive session, paste output here)

- Accept the workspace trust dialog (gotcha #15), then approve the project `.mcp.json` server

- `/context` — memory files, rules, skills, agents, MCP tools with token counts
- `/hooks` — six events registered from `.claude/settings.json`
- `/mcp` — `playwright` connected from project scope (approve on first run)
- `/agents` — four project agents
- `/memory` — CLAUDE.md, CLAUDE.local.md (after copying the example), auto-memory entry `flagpole-confirmed-decisions`
- `InstructionsLoaded`: copy the hook block from `.claude/settings.local.json.example`, start a session, read `backend/…py` after Phase 3, show `path_glob_match` in `.claude/logs/instructions-loaded.log`
- SessionStart: the "Session facts" reminder at the top of a new session
- `/speckit-constitution` re-run: reports no changes (constitution v1.0.0 already written)
