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

## Phase 3 — feature 001-flagpole-api via the SDD loop (2026-09-02)

| Step | Invocation | What happened (real output) |
|---|---|---|
| specify | `/speckit-specify 001-flagpole-api: …` | `create-new-feature.sh --json --number 1 --short-name flagpole-api` → `{"BRANCH_NAME":"001-flagpole-api","SPEC_FILE":".../specs/001-flagpole-api/spec.md","FEATURE_NUM":"001"}`; the script does not create the branch in v1.0.3 (`git switch -c 001-flagpole-api` by hand). Spec: 4 stories, 17 FRs, 7 SCs, 0 `[NEEDS CLARIFICATION]`; `checklists/requirements.md` 18/18. |
| clarify | `/speckit-clarify` | 4 questions (test auth, consumer auth, audit filter, concurrency), all answered "recommended". Spec gained `## Clarifications`, FR-007 filter, FR-011 "no switch that disables validation", FR-018 last-write-wins. |
| plan | `/speckit-plan <tech context>` | `setup-plan.sh --json`; plan.md (Constitution Check: 5/5 PASS), research.md (R1 injectable key resolver … R6 error shape), data-model.md, quickstart.md, contracts/openapi.yaml. |
| tasks | `/speckit-tasks` | 30 tasks, tests-first per story, 7 parallel groups. |
| analyze | `/speckit-analyze` | 0 CRITICAL, 1 MEDIUM (SC-006 latency vs constitution III → "measured, never asserted"), 4 LOW (naming, plan tree, contract 503, dev.sh scope). Coverage 100%. Fixes applied spec-first, committed `c648a00`. |
| implement | `/speckit-implement` | Red → green per story. Bugs found by the tests, not by reading: `JSONResponse` argument order, audit row flushed before its flag (FK), auth reading env settings instead of the app's, module-level app stealing the Prometheus registry, one-letter test keys violating FR-014. Final: `35 passed in 1.76s`; `make test-fast` = 29 hook tests + 35 pytest. |
| smoke | `uvicorn app.main:create_app --factory --port 18000` | `healthz {"status":"ok"}`, `readyz {"status":"ok"}`, `/flags` without token → 401, `/evaluate` without token → 401, openapi paths `["/audit","/evaluate","/flags","/flags/{key}/env/{env}","/healthz","/readyz"]`, 100 `http_*` metric lines. Seed twice: `seeded new_banner` then `seed already present`. |
| review | `code-reviewer` (general-purpose agent following the definition, gotcha #17) | `Verdict: request-changes`, 2 medium + 9 low: `print` in seed, `oidc_audience`/hard-coded JWKS vs `.env.example`, `flag_key` bounds not in contract, PUT key pattern, env-configurable operator group, process-global metrics guard, unused `env` setting, shallow contract test, no FR-016 test, missing docstrings, uncommitted gotcha rows. All fixed in `fix(api)`: 37 tests green. |

Hooks observed during implementation: the PostToolUse formatter ran on every Python file written (`ruff format` lines in `hooks.log`); the Stop gate ran `make test-fast` when backend files were dirty and blocked once with the failing-test tail while the suite was red.

## Phase 3 — feature 002-flagpole-web via the SDD loop (2026-09-02)

| Step | Invocation | What happened (real output) |
|---|---|---|
| specify | `/speckit-specify 002-flagpole-web: …` | Spec: 4 stories, 15 FRs, 4 SCs; `checklists/requirements.md` 18/18. |
| clarify | `/speckit-clarify` | 3 questions (create form in scope, explicit save vs autosave, real Dex now vs stub), batched into one `AskUserQuestion` (gotcha #18). Answers: small create form, explicit per-row Save, Dex in docker compose now. |
| plan | `/speckit-plan` | research.md F1–F6 (PKCE, token in memory only, generated types, Vite proxy, testids, Playwright webServer), `contracts/ui-contract.md` as the stable test surface. |
| tasks / analyze | `/speckit-tasks`, `/speckit-analyze` | 30 tasks; 0 CRITICAL, findings on FR traceability, SC measurement wording, and the 005 hand-off, fixed spec-first. |
| implement | `/speckit-implement` | Vitest first, then components. Real bugs the tests caught: jsdom cannot parse the relative `/api` base (tests use an absolute base), and React StrictMode redeemed the OIDC authorization code twice, so Dex answered `500` on the second `/token` call. Fixed by memoising the exchange per callback URL. |
| e2e | `npx playwright test` | `9 passed (9.6s)` against a real Dex, a migrated and seeded API and the Vite dev server, all started by `playwright.config.ts`. First run failed 4 tests with `new_banner` missing: the webServer command migrated but did not seed. |
| SC-005 | 10 consecutive runs | `9 passed` every time, 9.2–9.7 s. No retries configured (`retries: 0`), so a flake would have failed the run. |
| contract | `data-testid` audit | Every identifier in `contracts/ui-contract.md` exists in `frontend/src`; the audit found one undocumented element (`create-error`) and it was added to the contract, since the contract says the surface is a spec change. |
| a11y | manual pass | Errors switched from `role="status"` to `role="alert"`, the flag table gained a caption and `scope="col"` headers, and the empty actions header gained a visually hidden label. |
| pre-commit | `git commit` | Blocked on three hooks before anything landed: `end-of-file-fixer` (auto-fixed), `check-json` on the Vite JSONC tsconfigs, and gitleaks on a comment that looked like an API key. See gotchas #19 and #20. |

`npm test` stays at `8 files, 32 tests` and `make test` runs it together with `npm run api:types:check`, which regenerates the types from `specs/001-flagpole-api/contracts/openapi.yaml` and fails on any drift.

### The two agents on 002 (2026-09-02)

`ui-tester` (Playwright MCP, browser, against `make dev`) — four scenarios, all pass, and it reported
attribute values rather than expectations: `identity` `alice@flagpole.local`, `role` `operator`,
`env-tab-dev` `aria-selected="true"` with `env-tab-prod` `"false"`, caption `Flags in dev` vs
`Flags in prod`, dev `checked=true`/`40` against prod `checked=false`/`0`, and for bob every write
control `disabled=true` with `viewer-hint` count exactly 1. Screenshots in `docs/screenshots/002/`.

`code-reviewer` (read-only, on `git diff main...HEAD`) — **request-changes**, 24 findings, and it hit
its 25-turn limit before reporting the first time; resuming it with "report from what you already
have, at most 5 more tool calls" produced the report. What made it worth the tokens is that it ran
things instead of reading them: it discovered `tsc --noEmit` compiled zero files by running it, and
found the type error hiding in `tests/factories.ts` by pointing a compiler at a directory no
`tsconfig` covered. Highlights: a lint gate that could not fail, `strict` missing, audit `after`
typed as an impossible object, duplicate rows from a double-clicked "load older entries", tests that
pass with the feature broken, and a build-time OIDC issuer that would have broken feature 005.

All 24 were fixed or answered in `2a6bc9f` and `a472d58`. The unit suite went 32 → 44 tests, and each
new test was mutation-checked: removing the behavior it covers fails exactly that test and nothing
else.

| After the fixes | Result |
|---|---|
| `tsc -b --noEmit` over app + node + test projects | clean; planting `const _proof: number = "x"` in `tests/factories.ts` fails it |
| `make test` | 29 hook + 37 backend + contract check + 44 frontend |
| `make e2e` | `9 passed (9.5s)`, from a database deleted at the start of every run |
| `FLAGPOLE_WEB_PORT=18011 make e2e` | `9 passed (9.4s)` — Dex re-rendered and restarted for the new port |


## Phase 3 — feature 003-flagpole-consumer via the SDD loop (2026-09-02)

| Step | Invocation | What happened (real output) |
|---|---|---|
| specify | `/speckit-specify 003-flagpole-consumer: …` | Three stories: the flag changes what a visitor sees; the page survives a broken flag service; the decision is visible. One `[NEEDS CLARIFICATION]`, on how a service authenticates. |
| clarify | one batched question | The feature description assumed a client-credentials grant. Checking the provider's own discovery document first was what caught it: `grant_types_supported = [authorization_code, refresh_token, device_code, token-exchange]` — no such grant exists here. Four options were put to the user with their costs; they chose a service-signed token and a second trusted issuer. |
| spec-first amendment | `specs/001-flagpole-api/spec.md` | 001 had already answered "the consumer forwards the user's token" during its own clarify. That answer assumed a signed-in user, and this page has none, so the earlier clarification is marked superseded and FR-019 was added — **before** any code. |
| plan | `/speckit-plan` | research C1–C9. Notable restraint: no `respx` (httpx ships `MockTransport`), no cache, no retry, no circuit breaker — each recorded with the signal that would justify it later. |
| tasks / analyze | `/speckit-tasks` then the analysis pass | 31 tasks, then a coverage scan found **no task cited a requirement id**, so coverage could not be checked mechanically. Every task now names its FR, and the scan found two requirements with no test at all: FR-003 (never cache a decision) and FR-015 (no write path). Both are "must not" requirements — the kind that gets built right and regresses quietly. T010a and T022a cover them. |
| implement | tests first, per story | Two designs changed while the tests were being written, both for the better. See below. |

### What the tests changed

**The bypass guard fired on my own code.** 001 has a test asserting that a verify-signature-false
decode appears nowhere in `app/`. Reading the `iss` claim to pick an issuer tripped it. The guard is
right to be absolute, so the issuer is now read straight out of the payload segment as untrusted
text — there is no decode call that could ever be widened into a bypass.

**A hope about the client became a rule in the service.** FR-019 says service tokens carry no groups.
Writing the test for a service token that *claims* the operators group showed that the flag service
was trusting the consumer to behave. It now ignores groups on service tokens outright, so the viewer
ceiling holds no matter what the consumer mints.

**The route test was wrong about the framework.** `test_the_consumer_exposes_no_write_path` walked
`app.routes` for `APIRoute` instances and found only `/metrics` — this FastAPI version keeps included
routers nested rather than flattening them. A shallow pass would have reported a read-only surface no
matter what the routers contained. It now walks recursively, and adding a `POST /oops` proves it
fails.

### Live verification

```
US1  banner elements: 1        decision-enabled = true   reason = rollout_hit
US3  alice rollout_miss · bob rollout_hit · carol rollout_miss
     alice three times: rollout_miss / rollout_miss / rollout_miss
US2  flag service stopped -> http 200 in 0.050s, reason = service_unavailable, banner elements: 0
     readyz: {"status":"ok"}          <- deliberately still ready
     log: ConnectError: All connection attempts failed
     occurrences of "Bearer" or "eyJ" in the log: 0

SC-003  against a server that accepts and never answers, ceiling 2.0s:
        http 200 in 2.046s / 2.034s      healthy loads: 0.033-0.047s
        readyz during the hang: 200 in 0.0016s
```

`make test`: 29 hook + 46 backend + 47 consumer + 44 frontend.

### The 003 review (2026-09-02)

`code-reviewer`, read-only, with the new authentication path as its target: **request-changes**, 15
findings, each confirmed by running a probe rather than by reading. Three produced a server error
where a refusal belonged — a missing service key taking down *all* authentication including people's
sign-ins, a token whose payload decodes to a list crashing the service for an anonymous caller, and
the consumer's fail-safe leaking a 500 when its signing key was unusable.

The bug worth remembering: `bool(body["enabled"])` reads the string `"false"` as true, so a drifted
service would have shown the banner with the flag off. Typing the response was **not** enough —
pydantic's ordinary coercion also accepts `"yes"` — and my own new test caught that, which is why the
boundary now uses a strict boolean.

Two findings changed the contract rather than the code, both decided by the user:

| Question | Decision | Why |
|---|---|---|
| Should a service token name its environment? | Yes, and the service pins it | Nothing forced `dev` and `prod` to use different key pairs, so key separation was not a boundary anything enforced |
| Should a rotated key be picked up without a restart? | No — cached for the process lifetime | A mounted secret changing restarts the pod anyway; live reloading is complexity with no trigger, and the posture is now written into the contract |

Verified live afterwards: the same consumer reads `env_disabled` from a `dev` service and gets
`service_unavailable` with a logged `401` the moment that service is told it serves `prod`.

`contracts/service-token.json` now holds the machine-readable slice both suites assert against, so a
drift in claim names, algorithm or lifetime fails a test instead of only the demo.

`make test` after the fixes: 29 hook + 55 backend + 59 consumer + 44 frontend.

## Phase 3 — feature 004-flagpole-mcp via the SDD loop (2026-09-02)

`/speckit-specify` → the spec surfaced a conflict it could not settle: a service token grants viewer
rights (the rule 003 established), but this server's whole purpose is arranging state, which is a
write. That became the one clarification question, answered by granting operator rights **per service
issuer** — a slot in the flag service's configuration, not a claim in the token. `specs/001` was
amended (FR-020) and committed before a line of 004 was written, as in 003.

`/speckit-analyze` found three requirements with no verifying task — "holds no state", "never
reimplements the rollout rule", and the agent arranging a Given state without an operator sign-in.
The first two became source guards rather than prose, because a helpful later edit is exactly how a
cache or a second copy of the rule appears.

### What the SDK actually is (gotcha #8, confirmed)

```
$ uv run python -c "from mcp.server import MCPServer; import inspect; print(inspect.signature(MCPServer.tool))"
(self, name=None, title=None, description=None, annotations=None, icons=None, meta=None, structured_output=None)
```

`FastMCP` was renamed `MCPServer` in `mcp` 2.1.1. Code written against the older name does not import.

### One design decision changed by evidence

The first implementation validated tool arguments inside the tool and returned a message. A test
showed the SDK had already coerced `"yes"` to `True` from the `enabled: bool` annotation before that
check ever ran:

```
{'key': 'a_b', 'env': 'dev', 'enabled': 'yes', 'pct': 5} -> is_error=False  {"flag": ... "enabled": true ...}
```

Probing the SDK showed the annotations *are* the contract — it publishes them and enforces them:

```
{'key': 'a_b', 'env': 'dev', 'enabled': 'yes', 'pct': 5}  -> True  enabled  Input should be a valid boolean
{'key': 'a_b', 'env': 'dev', 'enabled': True,  'pct': 500} -> True  pct      Input should be less than or equal to 100
{'key': 'Bad', 'env': 'dev', 'enabled': True,  'pct': 5}   -> True  key      String should match pattern '^[a-z][a-z0-9_]{1,62}$'
{'key': 'a_b', 'env': 'staging', ...}                      -> True  env      Input should be 'dev' or 'prod'
```

So FR-008 was rewritten — spec first — to say the rules live in the published argument schema. The
assistant is told them in advance, a breaking call never reaches the flag service, and the duplicate
check inside the tool was deleted rather than kept for comfort.

### Live verification (2026-09-02)

The real process, over stdio, against a running flag service:

```
tools:     ['list_flags', 'get_flag', 'set_flag_state']
resources: ['flagpole://flags']
prompts:   ['rollout_check']

set_flag_state new_banner dev enabled=true rollout=100
  -> {"flag": {"key": "new_banner", "environments": {"dev": {"enabled": true, "rollout_percent": 100}, ...}}}

resource flagpole://flags -> {"flags": [{"key": "new_banner", ...}]}
prompt   rollout_check    -> Review the rollout of the Flagpole flag 'new_banner'. Its current state is: {...}
```

All three capability kinds exercised (SC-004). Then, with nothing restarted, the consumer:

```
$ curl -s "http://127.0.0.1:18020/?user=demo@flagpole.local"
decision-flag    new_banner
decision-env     dev
decision-user    demo@flagpole.local
decision-enabled true
decision-reason  rollout_hit
```

and the audit trail (SC-006) — the assistant is named as the actor, which is the truth:

```
$ curl -s -H "Authorization: Bearer $TOKEN" ".../audit?flag_key=new_banner"
{"items": [{"id": 1, "who": "flagpole-mcp", "flag_key": "new_banner", "env": "dev",
            "before": {"enabled": false, "rollout_percent": 0},
            "after":  {"enabled": true,  "rollout_percent": 100}}], "next_before": null}
```

The two failure paths that matter, verified against the real service rather than a stub. With the
flag service restarted holding `flagpole-mcp` in the **viewer** slot instead of the operator one:

```
read  -> {"flags": [{"key": "new_banner", ...
write -> {"error": {"kind": "forbidden",
                    "message": "This server has not been granted operator rights by the flag
                                service, so it can read flag state but not change it."}}
```

and with the flag service stopped altogether, every tool — none of them an error at the protocol
level, because a traceback gives an assistant no remedy:

```
list_flags     is_error=False -> {"error": {"kind": "unreachable", "message": "The flag service at http://127.0.0.1:18000 could not be reached."}}
get_flag       is_error=False -> {"error": {"kind": "unreachable", ...}}
set_flag_state is_error=False -> {"error": {"kind": "unreachable", ...}}
```

An environment claim minted for `prod` against a dev-configured service: `401`. A dev token in the
operator slot writing: `201`/`200`. The same token with `groups: ["operators"]` when the deployment
put it in the viewer slot: `403` — the role is the slot's, never the token's.

### Mutation checks

Three guarantees, each removed to confirm exactly one test notices:

| Removed | Result |
|---|---|
| the 403 branch (a refused write becomes an outage) | 2 failed |
| `StrictBool` on `enabled` | 6 failed |
| the resource caching its answer | 1 failed |

A fourth mutation *survived*: emptying a service token's groups turned out to be dead code once the
role came from the slot. It was deleted rather than kept — the guarantee is now structural, and a
later mutation confirmed a service token cannot reach the group rule at all.

### Suites after 004

```
hook tests: 29 passed
backend:    67 passed
consumer:   59 passed
mcp:        61 passed
frontend:   44 passed (10 files)
```

## Phase 4 — feature 005-platform-delivery via the SDD loop (2026-09-02)

Two questions were put to the user before any manifest was written, because either answer changed
them materially: **one database per environment** (so isolation is something the network enforces,
not something credentials claim) and **bootstrap rather than a read-only source** (so upgrading the
reconciler is also a commit). Both are recorded as clarifications in the spec.

`scripts/verify-cluster.sh` was written **first**, against an empty cluster, and failed 37 of 42.
A check written after the manifests tends to describe whatever they happen to do.

### What running it disproved

Five things were wrong in ways that reading could not have caught. Each is now a gotcha.

| What failed | Why | Gotcha |
|---|---|---|
| Nothing installed at all | Flux dry-runs a Kustomization's **whole** set, so `ClusterIssuer` in the same unit as cert-manager aborted the apply that would have installed cert-manager. A deadlock, not a delay. | #30 |
| Traefik install rejected | Chart 41.x moved `redirections` and `tls` under `http`, and split `logs` into `log` and `accessLog`. | — |
| Dex pods never created | The chart sets no security context and the namespace enforces `restricted`; the HelmRelease said only "timeout waiting for Deployment" and the real reason was in the ReplicaSet's events. | #31 |
| Dex crash-looped | It expands its config into `/tmp`, which a read-only root filesystem forbids. | — |
| The operator-grant check passed for the wrong reason | It read the container's inline `env`, but the setting arrives through `envFrom` — so "absent" was both what it expected and all it could ever find. A check that cannot fail is not a check. | #32 |

And two the cluster caught that a local run never would:

- **The ingress passed `/api` through unchanged.** The development proxy strips it, so every API call
  would have worked locally and 404'd in the cluster. A strip-prefix middleware fixes it — and being
  a Traefik custom resource, it needed the same `dependsOn` lesson as the certificate authority.
- **The consumer could not reach the flag service.** Deny-first network policy admitted only Traefik
  to the flag service, so evaluation was refused at the far end. The consumer did exactly what it
  should — HTTP 200, `service_unavailable`, no banner — which is precisely why this looked like a
  working system. A fail-safe hides a broken dependency; the check has to assert the *reason*.

### The cluster, verified

```
$ flux get kustomizations
flagpole-dev     005-platform-delivery@sha1:...  True  Applied revision
flagpole-prod    005-platform-delivery@sha1:...  True  Applied revision
flux-system      005-platform-delivery@sha1:...  True  Applied revision
platform         005-platform-delivery@sha1:...  True  Applied revision
platform-issuer  005-platform-delivery@sha1:...  True  Applied revision

$ scripts/verify-cluster.sh
43 passed, 0 failed
```

The assistant's own MCP server, pointed at each environment through the ingress (SC-007):

```
dev   list_flags      -> {"flags": [{"key": "new_banner", ...}]}
dev   set_flag_state  -> {"flag": {"environments": {"dev": {"enabled": true, "rollout_percent": 100}}}}
prod  list_flags      -> {"error": {"kind": "unauthorized", "message": "... refused this server's credentials."}}
prod  set_flag_state  -> {"error": {"kind": "unauthorized", "message": "... refused this server's credentials."}}
```

Production refuses it at *authentication*, not authorization: that overlay names no slot for the
assistant's issuer at all, so the public key it holds is inert. That is stronger than the design
described, and the comment beside the secret was corrected to say so.

Then the two consumers, with nothing restarted (SC-002):

```
consumer.dev.flagpole.localhost    enabled=true   reason=rollout_hit
consumer.prod.flagpole.localhost   enabled=false  reason=env_disabled
```

Each environment shows its own state. Isolation, from a pod that was already running:

```
PASS  flagpole-dev cannot reach flagpole-prod on 5432
PASS  flagpole-prod cannot reach flagpole-dev on 5432
PASS  flagpole-dev rejects a privileged Pod
PASS  flagpole-prod rejects a privileged Pod
```

GitOps, both directions (SC-003):

```
$ git commit && git push && flux reconcile ...
  after the commit:            flagpole-gitops-demo   1   3s
$ git rm && git commit && git push && flux reconcile ...
  after removing it from git:  Error from server (NotFound): configmaps "flagpole-gitops-demo" not found
```

And the guard, refusing to let the cluster be edited by hand at all:

```
$ kubectl scale deploy/flagpole-api -n flagpole-dev --replicas=3
gitops-guard: 'kubectl scale' outside flux-system is denied. Flux owns this cluster: edit the
manifest under deploy/, commit, then run 'flux reconcile kustomization <name> --with-source'.
```

### Two things you must run yourself

The guard is stricter than the plan described — it refuses hand edits in **every** namespace but
`flux-system`, not only `flagpole-*`. So drift correction cannot be demonstrated from inside a
session without disabling the guard, which would be the wrong lesson. Run it yourself:

```
! kubectl -n traefik scale deploy/traefik --replicas=3   # then watch Flux put it back
```

And to open the hosts in your own browser without a certificate warning, trust the cluster's CA. This
needs `sudo`, so it is printed and not run:

```
kubectl -n cert-manager get secret flagpole-ca -o jsonpath='{.data.tls\.crt}' | base64 -d > /tmp/flagpole-ca.crt
sudo cp /tmp/flagpole-ca.crt /usr/local/share/ca-certificates/flagpole-ca.crt && sudo update-ca-certificates
```

`.mcp.json` now passes `--ignore-https-errors` to the Playwright server so the `ui-tester` agent can
reach the cluster hosts; that takes effect in a new session.


## Phase 5 — feature 006-ci-and-security via the SDD loop (2026-09-02)

Two workflows, one Renovate configuration, one scanner script and one findings document. The lesson
of this feature is not that scanners exist; it is what happens to what they say.

### The check was written before the thing it checks

`scripts/check-ci-contract.sh` reads `specs/006-ci-and-security/contracts/ci-contract.json` and was
run first against a repository with no workflows at all — **2 passed, 14 failed**. After the
workflows, the configuration and the findings document:

```
105 passed, 0 failed
```

Neither refusal is taken on trust. Changing `pull_request` to `pull_request_target` in `ci.yml`:

```
  FAIL triggers on pull_request
  FAIL no 'pull_request_target' in any workflow
103 passed, 2 failed
```

Adding a step that writes to the cluster (FR-006):

```
  FAIL no 'kubectl' in any workflow
104 passed, 1 failed
```

### What the first real scan found — in itself

`make scan` had never run before this feature; `scripts/scan.sh` was a four-line stub. Its first run
reported 12 findings, and four of them were bugs in the scanning rather than in the code:

| Reported | What it actually was |
|---|---|
| 6 x bandit HIGH in `pygments`, `cryptography`, `httpx`, the MCP SDK | `bandit -r mcp/flagpole-mcp` descended into the service's `.venv` and reported its dependencies as this repository's source |
| `private-key` in `consumer/.keys/`, `mcp/flagpole-mcp/.keys/` | gitleaks and trivy were walking gitignored local dev keys — reporting the developer's machine rather than the repository. `git ls-files` returns nothing for either path |
| trivy: **clean** on `deploy`, `platform`, `clusters` | `trivy config` takes one directory and exits FATAL on three. The report was empty, `jq` extracted nothing, and the summary said clean. A check that could never fail — the exact FR-011 failure this feature exists to prevent, found by the feature's own first run |
| KSV-0014 on `postgres` | Real. `readOnlyRootFilesystem: false`, behind a comment claiming PostgreSQL needs a writable root. It needs two directories, not a filesystem |

The postgres finding was fixed rather than accepted, and verified before the manifest changed:

```
docker run --read-only --tmpfs /var/run/postgresql --tmpfs /tmp -v vol:/var/lib/postgresql/data ...
READY after 2s
127.0.0.1:5432 - accepting connections
CREATE TABLE / INSERT 0 1 / count = 1
touch: /usr/local/probe: Read-only file system
```

What remains is two `accepted` rows in `docs/security-findings.md` for Flux's own generated RBAC —
`kustomize-controller` cannot manage Secrets without permission to manage Secrets.

### Both guarantees, proved by breaking them

A planted credential must fail the run. The first attempt used the AWS documentation example and
produced nothing — gitleaks allowlists it (gotcha #38). With a realistically shaped token:

```
== gitleaks — secrets in the tree and its history (any finding)
   1 finding(s) at or above the threshold
     github-pat backend/app/_probe.py:2
exit=1
```

A scanner that is not installed must fail, not be skipped (FR-011). With `gitleaks` removed from
`PATH`:

```
== gitleaks — secrets in the tree and its history (any finding)
   NOT INSTALLED — mise use -g gitleaks
...
gitleaks       missing    0
exit=1
```

### The state it settles at

```
== triage against docs/security-findings.md
   recorded    KSV-0041
   recorded    KSV-0046
   every finding above its threshold has a row

SCANNER        STATE      FINDINGS
pip-audit      clean      0
npm-audit      clean      0
osv-scanner    clean      0
trivy          flagged    2
hadolint       clean      0
gitleaks       clean      0
bandit         clean      0
semgrep        clean      0

all scanners ran; nothing unaccounted for
raw output: .scan
```

### A note the discovery phase got wrong

`renovate-config-validator` does **not** reject the deprecated `fileMatch` key. It migrates it,
warns, and exits 0:

```
 WARN: Config migration necessary
 WARN: Config migration diff:
 INFO: Config validated successfully against 1 file(s)
$ echo $?
0
```

So the lint job reads the validator's output rather than its exit status, and the contract check
asserts the key is absent. Recorded as gotcha #35 and corrected in `research.md`.

### What the review changed (2026-09-02)

The `code-reviewer` agent returned **request-changes** on the 006 diff: 15 findings, 5 high. Three
of them were the same shape as the bug the feature had already caught in itself, which is the part
worth keeping:

| Finding | Why it mattered |
|---|---|
| FR-011 enforced for trivy only | The other seven scanners piped `jq` over their output with stderr discarded. An errored scanner produced an empty `.ids` file and was recorded **clean** — fixed for one tool, left in place for seven |
| `trivy fs` and `trivy config` never look inside an image | Adding `trivy image` over the three digest-pinned bases surfaced **28 HIGH/CRITICAL CVEs** that no scanner had ever reported, while the contract recorded trivy's coverage as "images and manifests" |
| `renovate.json` disabled this repository's own images | Which is exactly the `deploy/` bump SC-005 depends on — while a comment in the same file claimed it was what proposed them |
| `[.. \| .automerge? // empty] \| all(. == false)` | jq's `//` treats `false` as absent, so the array is always empty and `all` on an empty array is `true`. A check that could never fail, inside the checker written to catch checks that can never fail |

The 28 base-image CVEs are now recorded: 15 `deferred` on an upstream rebuild — the pinned digests
*are* what `python:3.12-slim`, `node:24-alpine` and `nginx-unprivileged:1.29-alpine` resolve to
today, so there is nothing to bump yet — and 14 `accepted` where Debian has published no fix at all.
Renovate's `dockerfile` manager is what closes the deferred ones.

Every repaired assertion was then mutation-tested. `automerge: true`, a scanner named in a banner but
never invoked, the `tags:` block deleted with its comment left behind, and a script writing `VERSION`
mid-line all turn the contract red.

### The merge, and what it published

```
release  success   preflight -> publish (flagpole-api | flagpole-consumer | flagpole-web)

flagpole-api         0.1.0 and sha-98972cb -> sha256:94df9c73b0bd617f7d0…
flagpole-consumer    0.1.0 and sha-98972cb -> sha256:a13e81cc8cb6e0392f5…
flagpole-web         0.1.0 and sha-98972cb -> sha256:e5e9ffe6e39cd745619…

org.opencontainers.image.revision = 98972cbf019fa100456857147278aea015cc4b94   (= main)
```

The republish guard, evaluated against the registry as it now stands:

```
::error file=VERSION::ghcr.io/randaguiac20/flagpole-{api,consumer,web} already published at 0.1.0
```

And the cluster, which follows `main`, took the postgres change where it actually runs:

```
✔ applied revision main@sha1:98972cbf…
flagpole-dev   readOnlyRootFilesystem=true  ready=true
flagpole-prod  readOnlyRootFilesystem=true  ready=true
$ kubectl -n flagpole-dev exec postgres-0 -- touch /usr/local/probe
touch: /usr/local/probe: Read-only file system
$ scripts/verify-cluster.sh
43 passed, 0 failed
```
