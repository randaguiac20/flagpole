# Tutorial — learn Claude Code by taking Flagpole apart

Thirteen lessons, in the order the concepts build. You clone this repository, run real commands
against a real service, and meet each Claude Code mechanism at the moment it becomes the cheapest
thing that solves the problem in front of you.

This is the only document here written **forwards**. `docs/walkthrough.md` is a record of what was
built, `docs/BLUEPRINT.md` is a rebuild recipe for someone who already knows this material, and
`docs/claude-code/*.md` are reference pages. They are all better than this file at what they do.
None of them can be read in order by a beginner. That is what this is for.

## Who this is for

Anyone who has used Claude Code as a chat window and wants to know what the other mechanisms are,
when to reach for each, and — the part almost nothing teaches — **when not to**. No Kubernetes
knowledge is needed before lesson 10. No Python or TypeScript is needed at all: you read code here,
you never write it.

## How each lesson works

Every lesson has the same seven beats. The important one is the sixth.

| Beat | What happens |
|---|---|
| 1. The problem | A real annoyance, in this repository |
| 2. The cheapest fix | Try the lower-cost mechanism first |
| 3. Why that is not enough | The specific point where it fails |
| 4. The mechanism | The actual file here that solves it |
| 5. Prove it works | Run a command, compare your output to the one shown |
| 6. **Prove it bites** | Deliberately break it and watch it fail |
| 7. How far | When this mechanism becomes the wrong answer |

Beat 6 exists because this repository has caught itself four times shipping a check that passed
while doing nothing — `docs/gotchas.md` rows **#37**, **#42**, **#50** and **#52**. One of those was
found *while writing this tutorial*, by running its own lesson 4. A guard you have never seen fail
is a guard you are trusting on faith.

## Time budget

| Lessons | Time | You need |
|---|---|---|
| 0–3 | ~30 min | A terminal. Nothing else. |
| 4–6 | ~30 min | Same. |
| 7–9 | ~45 min | Docker running. |
| 10–11 | ~2 h | Docker, ports 80 and 443 free, a GitHub account |
| 12 | open-ended | Your own empty repository |

**Stopping after lesson 9 is a complete course.** Lessons 10–11 add the cluster, which teaches
GitOps and secret handling, not Claude Code. Stop where it stops being useful to you.

## The spine: one question, asked seven times

Every mechanism in this repository was chosen by walking this list from the top and stopping at the
first "yes". It is `templates/PROMPT.md` §2.1, and it is also the order of the lessons below.

1. Can built-in tools plus one line in `CLAUDE.md` do this? **Stop there if so.**
2. Is it always-on context, or on-demand? Always-on → memory or a rule. On-demand → a skill.
3. Must it hold every time, regardless of what Claude decides? → a **hook**, or `permissions.deny`.
4. Would it flood the conversation, or need isolation? → a **subagent**.
5. Does Claude need a system it cannot reach through the shell? → **MCP**.
6. Will a second repository need the identical setup? → a **plugin**. Otherwise keep it in `.claude/`.
7. Is this user-visible behaviour, or a chore? Behaviour goes through **spec-driven development**.

The cost rises at every step. Most of what people build as a hook is a rule; most of what people
build as an MCP server is a shell command.

---

# Lesson 0 — get it running

```bash
git clone https://github.com/randaguiac20/flagpole.git
cd flagpole
make bootstrap
```

`make bootstrap` checks your tools, creates `.env`, installs the Python and Node dependencies and
the Chromium that Playwright needs, creates an age key **outside** the repository, and installs the
pre-commit hook. It runs no `sudo` and is safe to re-run.

If it stops at "tools", it lists everything missing at once rather than the first one. Versions are
pinned in `.mise.toml`; `mise install` fetches the set.

Now the fastest honest proof the repository works — no network, no cluster, no Claude:

```bash
make test-hooks
```

```
gitops-guard.sh   9 cases ok · secret-guard.sh 8 cases ok · format.sh 3 · stop-tests.sh 5 · notify.sh 1 · session-start.sh 1 · instructions-loaded.sh 2
hook tests: 29 passed, 0 failed
```

Then see what you have:

```bash
make help
```

```
  help           list targets
  bootstrap      check tools, install deps, create the age key OUTSIDE the repo, install pre-commit
  dev            run api/web/consumer/dex locally on the ports from .env(.example)
  test           all unit tests + contract drift check (backend, consumer, mcp, frontend)
  test-fast      the subset the Stop hook runs (< 60 s): hook tests + python unit tests
  test-hooks     shell tests for every hook, fed with sample stdin JSON
  scan           all scanners (pip-audit, npm audit, osv-scanner, trivy, hadolint, gitleaks, bandit, semgrep)
  build          docker images for api, consumer, web
  cluster-up     k3d cluster (Traefik disabled) + flux bootstrap github (asks before touching GitHub)
  deploy         import images into k3d, reconcile Flux, wait for Ready
  e2e            Playwright headless (starts API, Dex and the web dev server itself)
  clean          remove local build/test artifacts (never the cluster, never keys)
```

**Work up this ladder, in order:** `make test-hooks` → `make test-fast` → `make dev` → `make e2e`.
Leave `scan`, `build`, `cluster-up` and `deploy` until lesson 10.

Finally, start Claude Code in the repository. You will be asked to **trust the folder** — accept it.
Until you do, project `permissions.allow` entries are ignored and you will see
`Ignoring 31 permissions.allow entries … this workspace has not been trusted` (gotcha #15). Deny
rules still apply.

Then ask it: `/context`. That shows what was loaded into the session before you typed anything.
Lesson 1 is about why.

---

# Lesson 1 — memory (`CLAUDE.md`)

**Problem.** Claude does not know your ports, your service names, or that `main` is protected. You
retype it every session.

**Mechanism.** `CLAUDE.md` at the repository root, loaded into every session automatically.

```bash
wc -l CLAUDE.md          # 57
head -20 CLAUDE.md
```

Read it. Notice what is *not* there: no architecture essay, no API reference, no "always run ruff
after editing Python". It is a table of where things are, a list of commands, and the names to use
verbatim. It imports exactly one file, `@docs/architecture.md`.

**Prove it works.** In a session, ask: *"what port does the API run on?"* It answers 18000 without
searching, because the fact is already in context.

**Prove it bites — it does not.** `CLAUDE.md` says "never `kubectl apply` into `flagpole-*`". Ask
Claude to do it anyway and it will usually refuse, citing the file. Now notice what just happened:
it *chose* to comply. Nothing stopped it. A line in `CLAUDE.md` is a **request**, not a guarantee.
That distinction is the entire reason lessons 3 and 4 exist.

**How far.** Every line here is paid for on every single request. The reference cap is 200 lines;
this repository holds itself to 150 and uses 57. When you want to add a paragraph, ask whether it
belongs in a rule (lesson 2) or a skill (lesson 5) instead.

→ `docs/claude-code/memory.md` · `docs/decisions/claude-md.md`

---

# Lesson 2 — rules (path-scoped memory)

**Problem.** Python conventions matter when editing Python. They are noise when editing a manifest.
Putting all of it in `CLAUDE.md` makes every session pay for all of it.

**Mechanism.** `.claude/rules/*.md`, each with a glob. They load only when a matching file is touched.

```bash
ls .claude/rules/
head -6 .claude/rules/python-services.md
```

```
frontend.md  kubernetes-manifests.md  python-services.md  workflow.md
```

Three are path-scoped. One — `workflow.md` — is always on, because "spec before code" and "never
commit a plaintext Secret" apply no matter what you are editing.

**Prove it works.** Ask Claude to edit `backend/app/auth.py`, then run `/context`. The Python rule
is loaded. Ask it to edit `deploy/base/api/deployment.yaml` instead and the Kubernetes rule loads in
its place.

**How far.** Overlapping globs are the failure mode. If `**/*.py`, `backend/**` and `**` all carry
Python advice, they will contradict each other and the reference says Claude picks one arbitrarily.
Keep the globs disjoint, one topic per file.

→ `docs/claude-code/rules.md` · `docs/decisions/rules.md`

---

# Lesson 3 — settings and permissions

**Problem.** Lesson 1 ended with a request that can be declined. Some things must not be up for
discussion.

**Mechanism.** `.claude/settings.json`, checked into the repository so everyone who clones it gets
the same floor.

```bash
jq -c '.permissions | {allow: (.allow|length), ask: (.ask|length), deny: (.deny|length)}' .claude/settings.json
jq -r '.permissions.deny[]' .claude/settings.json
```

```
{"allow":31,"ask":5,"deny":16}
```

Three lists, three meanings: **allow** runs without asking, **ask** prompts you, **deny** is refused
outright. `git push` is in `ask` — it reaches outside the repository. `rm -rf *`,
`kubectl delete *`, `sops --decrypt *`, and reading `**/.env` or `**/*.agekey` are in `deny`.

**Prove it bites.** Ask Claude to run `rm -rf build/`. It is refused before anything executes, and
the refusal names the rule. Ask it to `git push` and you get a prompt instead.

**How far.** Deny rules are patterns. They cannot say "`kubectl apply` is fine in `flux-system` but
not in `flagpole-dev`", because that needs the *arguments* parsed, not matched. That exact gap is
lesson 4.

→ `docs/claude-code/settings.md` · `docs/decisions/settings-permissions.md`

---

# Lesson 4 — hooks (enforcement that reads content)

**Problem.** Two rules this repository cannot express as patterns:

- `kubectl apply` is allowed in `flux-system` and denied everywhere else — needs the verb *and* the namespace.
- A `kind: Secret` may be committed only if it is SOPS-encrypted — needs the file's **content**, which does not exist yet when the pattern is checked.

**Mechanism.** Shell scripts registered against events in `.claude/settings.json`.

```bash
ls .claude/hooks/*.sh
```

| Hook | Fires on | What it does |
|---|---|---|
| `session-start.sh` | `SessionStart` | Injects branch, cluster, Flux and key facts — things too volatile for `CLAUDE.md` |
| `gitops-guard.sh` | `PreToolUse` (Bash) | Denies cluster mutations outside `flux-system` |
| `secret-guard.sh` | `PreToolUse` (Edit/Write) | Denies a plaintext `kind: Secret` under `deploy/` or `clusters/` |
| `format.sh` | `PostToolUse` | Runs ruff or prettier on the file just written |
| `stop-tests.sh` | `Stop` | Runs `make test-fast` before the turn can end |
| `notify.sh` | `Notification` | Desktop notification on a permission prompt |

**Prove it bites.** A hook is just a program that reads JSON on stdin, so you can fire one by hand
with no Claude session at all. **Run this in a plain terminal, not through Claude:**

```bash
jq -nc --arg c 'kubectl apply -k deploy/overlays/dev' \
  '{hook_event_name:"PreToolUse",tool_name:"Bash",tool_input:{command:$c}}' \
  | .claude/hooks/gitops-guard.sh
```

```
gitops-guard: 'kubectl apply' outside flux-system is denied. Flux owns this cluster…
```

Now swap `-k deploy/overlays/dev` for `-n flux-system` and watch it allow. That single difference is
the reason this is a hook and not a deny rule.

**Why "in a plain terminal"?** If you ask Claude to run that command, the guard denies it — the hook
reads the whole command string and cannot tell *writing about* `kubectl apply` from *running* it.
That is gotcha **#27**, and it is a real design cost of hooks, not a bug.

**How far.** Hooks run on every matching event, so they must be fast and they must not be chatty.
`format.sh` fails open (a formatter that breaks should not block your work); the two guards fail
**closed** (a guard that breaks must not silently permit). Choose that direction deliberately.

→ `docs/claude-code/hooks.md` · `.claude/hooks/tests/run.sh`

---

# Lesson 5 — skills (procedures, on demand)

**Problem.** "Build the images, import them into k3d, reconcile Flux, wait for Ready, then verify"
is six commands in a fixed order with real branching. Pasting it every time is how steps get skipped.

**Mechanism.** A folder with a `SKILL.md`. Loaded only when invoked, so it costs nothing until used.

```bash
ls .claude/skills/ plugins/flagpole-tools/skills/
head -8 .claude/skills/api-conventions/SKILL.md
```

Five skills, and the differences between them are the lesson:

| Skill | Who can invoke it | Why |
|---|---|---|
| `add-flag-field` | you or Claude | A checklist Claude should reach for on its own |
| `api-conventions` | **Claude only** (`user-invocable: false`) | Reference knowledge, not a command you type |
| `e2e` | you or Claude | Safe to run any time |
| `deploy-local` | **you only** (`disable-model-invocation: true`) | Changes the cluster |
| `security-scan` | **you only** | Slow, noisy, and delegates to an agent |

**Prove it works.** Run `/flagpole-tools:e2e`. It shows the live port table first, runs Playwright
headless, and summarises. Expect `9 passed`.

**How far.** A skill per Makefile target is the classic mistake — `/build`, `/test`, `/lint` each
restating one line. If the procedure has no branching and no judgement, it is a Makefile target and
Claude can already run it.

→ `docs/claude-code/skills.md` · `docs/anti-patterns.md`

---

# Lesson 6 — subagents (isolation)

**Problem.** Eight scanners produce thousands of lines. Reviewing a diff means reading many files.
Both flood the conversation you are trying to have, and you pay for that context for the rest of the
session.

**Mechanism.** A subagent runs in its own context and returns only a conclusion.

```bash
ls .claude/agents/ plugins/flagpole-tools/agents/
grep -A3 '^description:' .claude/agents/code-reviewer.md
```

| Agent | Tools it is allowed | Point |
|---|---|---|
| `code-reviewer` | Read, Grep, Glob, `git diff/log/status` | **Cannot edit.** A reviewer that fixes things is not a reviewer |
| `ui-tester` | Playwright + flagpole-mcp only | Drives the browser, returns pass/fail |
| `security-auditor` | the scanners | Its own file says it exists because the output would flood the session |
| `deploy-verifier` | read-only `kubectl` / `flux` | Checks the cluster, changes nothing |

Every one is read-only by construction. That is not politeness — it is the tool list.

**Prove it works.** Make a small change, then ask for the `code-reviewer` agent. You get findings,
not a wall of file contents, and your main context is barely touched.

**How far.** A subagent cannot see your conversation and you cannot see its work. That isolation is
the feature and the cost. For a two-file change, reviewing inline is cheaper and better.

→ `docs/claude-code/agents.md`

---

# Lesson 7 — MCP (reaching what the shell cannot)

**Problem.** Claude can run `curl`. It cannot click a button, and it cannot see that the banner
rendered.

**Mechanism.** MCP servers, declared in `.mcp.json`. You approve them on first run.

```bash
jq -r '.mcpServers | keys[]' .mcp.json
```

| Server | Why it earns its place |
|---|---|
| `playwright` | A real browser. There is no shell command for "is the checkbox disabled?" |
| `flagpole-mcp` | This repository's own server: 3 tools, 1 resource, 1 prompt |

Start the stack first — `flagpole-mcp` talks to the API on 18000:

```bash
make dev          # leave running in another terminal
```

Then ask Claude to list the flags. It calls `list_flags` rather than shelling out.

**How far — and this is the honest part.** `flagpole-mcp` wraps an HTTP API that `curl` could reach.
A skill with three `curl` commands would have worked. It exists because building one is worth
learning and because `ui-tester` uses it to set state before browsing. `docs/decisions/` says so in
writing, and `docs/anti-patterns.md` records a second MCP server that was **designed and then not
built** because `kubectl` already existed. If a CLI can do it, prefer Bash and a skill.

→ `docs/claude-code/mcp.md` · `mcp/flagpole-mcp/`

---

# Lesson 8 — plugins (packaging, and its price)

**Problem.** You have skills and agents worth sharing across repositories.

**Mechanism.** A plugin bundles them; a marketplace serves it. Here the marketplace is this very
repository.

```bash
claude plugin details flagpole-tools@flagpole-local
```

```
Component inventory
  Skills (3)  deploy-local, e2e, security-scan
  Agents (2)  security-auditor, deploy-verifier

Projected token cost
  Always-on:   ~510 tok   added to every session
```

**That number is the lesson.** Five small components cost ~510 tokens in **every** session, whether
you invoke them or not. Packaging also costs a namespace: everything became
`flagpole-tools:deploy-local`, and every cross-reference had to move with it.

**How far.** For a single repository, `.claude/` costs nothing, needs no manifest, no marketplace and
no namespace. This plugin exists to demonstrate the mechanism, and `docs/decisions/plugin-flagpole-tools.md`
says exactly that rather than inventing a better reason. Reach for a plugin when a *second*
repository needs the identical set.

→ `docs/claude-code/plugins.md` · gotchas #44, #45, #46

---

# Lesson 9 — spec-driven development

**Problem.** "Add a rollout schedule" becomes code before anyone agrees what it means, and the tests
end up asserting whatever got written.

**Mechanism.** Spec Kit. Behaviour is decided in `specs/`, and code follows.

```
/speckit-specify → /speckit-clarify → /speckit-plan → /speckit-tasks → /speckit-analyze → /speckit-implement
```

The best worked example is the first feature — read it in this order:

```bash
ls specs/001-flagpole-api/
sed -n '1,40p' specs/001-flagpole-api/spec.md          # what and why, no technology
sed -n '1,30p' specs/001-flagpole-api/plan.md          # how, with the stack
sed -n '1,25p' specs/001-flagpole-api/tasks.md         # numbered, each naming a file
cat specs/001-flagpole-api/quickstart.md               # commands + a table of curl proofs
```

`quickstart.md` is the single best hands-on page in the repository: setup commands, seven `curl`
scenarios each mapped to a requirement, and a dated block of real output.

**Prove it bites.** `/speckit-analyze` is the gate. It reads spec, plan and tasks together and
reports requirements with no task, tasks with no requirement, and contradictions. It found real gaps
in this repository before implementation started.

**How far.** Chores do not get a spec. Hooks, CI, formatter config and documentation are committed
straight to `main` — `.claude/rules/workflow.md` says so. Specs are for user-visible behaviour.

→ `docs/claude-code/sdd.md`

---

# Lesson 10 — the cluster (optional, ~2 hours)

From here on you are learning GitOps rather than Claude Code. Skip freely.

**Read [Appendix A](#appendix-a--trusting-the-local-ca) first** — without it your browser refuses
every cluster host and the failure looks like a broken cluster.

```bash
make cluster-up     # asks before it touches GitHub
make build
make deploy
```

`cluster-up` announces its two outside-the-repository effects — binding ports 80/443, and pushing
Flux's manifests to your GitHub remote — and stops for an answer on the second.

**Prove it works.**

```bash
scripts/verify-cluster.sh
```

**Prove it bites.** Change something by hand and watch Flux put it back:

```bash
kubectl -n traefik scale deploy/traefik --replicas=3
flux get kustomizations          # then look again in a minute
```

Flux owns the cluster. Your edit is drift, and drift gets reverted. This is also why
`gitops-guard.sh` exists: it stops Claude making a change that was always going to be undone.

**A caution this repository learned the hard way.** `make e2e` runs against **localhost only** —
`playwright.config.ts` hardcodes the base URL and starts its own stack. A green suite says the code
is right, not that the cluster is. In September 2026 all nine tests passed while every cluster user
was signed in with the wrong role, because the cluster ran Dex 2.44.0 and the local stack ran 2.45.1
(gotchas **#49**, **#50**). Verify the deployed system against the deployed system.

---

# Lesson 11 — CI, scanning, dependency updates

```bash
make scan
```

Eight scanners. Three rules worth stealing:

- A scanner that did not really run is a **failure**, not a skip. "Missing tool" and "no findings" must never produce the same result (gotcha #37).
- The script never uses `set -e`. Independent checks all run, and it fails once at the end with the whole list — otherwise you get one run per fix (gotcha #36).
- A finding above threshold fails the build until it has a **row** in `docs/security-findings.md` with a decision. Triage is a file, not a memory.

**Prove it bites.** Plant a realistically shaped secret and watch gitleaks catch it:

```bash
printf 'TOKEN = "ghp_%s"\n' "$(head -c 27 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9' | head -c 36)" \
  > backend/app/_probe.py
make scan            # gitleaks: 1 finding, exit 1
rm backend/app/_probe.py
```

Use a random value. The well-known AWS documentation example is **allowlisted**, so a probe built
from it reports nothing and you conclude the scanner is broken when it is working perfectly
(gotcha #38).

Dependency updates are Renovate's, via the Mend GitHub App — nine managers, digests pinned, no
automerge. See `docs/renovate.md`.

---

# Lesson 12 — now do it yourself

```bash
ls templates/
cat templates/README.md
```

`templates/` holds a de-Flagpoled copy of every mechanism, with the placeholders written
`<LIKE THIS>`. Its README table has a column most such tables omit: **"Do not, when"**.

Then either:

- **Start a new repository like this one** — paste `templates/PROMPT.md` as the first message in a fresh session at the root of an empty repository, replacing every placeholder.
- **Rebuild this one** — `docs/BLUEPRINT.md`, asserted by `scripts/check-blueprint.sh`.

Whatever you build, keep the habit that made this repository worth reading: **prove every guard by
breaking it first.** Fifty-nine rows in `docs/gotchas.md` exist because someone ran the command
instead of trusting the documentation — including four checks that passed while doing nothing at
all, one of which was found by running lesson 4 of this tutorial.

---

# Appendix A — trusting the local CA

The cluster issues its own certificates. Nothing trusts them until you say so, and **Linux has three
separate trust stores** — this is where the first attempt here stopped one step short.

Export the certificate once:

```bash
kubectl -n cert-manager get secret flagpole-ca -o jsonpath='{.data.tls\.crt}' | base64 -d > /tmp/flagpole-ca.crt
```

| Store | Who reads it | How |
|---|---|---|
| System | `curl`, `openssl` | `sudo cp /tmp/flagpole-ca.crt /usr/local/share/ca-certificates/ && sudo update-ca-certificates` |
| NSS | **Chrome, Chromium** | `certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n flagpole-ca -i /tmp/flagpole-ca.crt` (needs `libnss3-tools`) |
| Firefox | Firefox only | Settings → Privacy & Security → Certificates → Authorities → Import. A snap build cannot read `/tmp` — copy the file to your home directory first. |

**Then quit your browser completely and reopen it.** Chrome reads NSS at startup, so a window that
was already open keeps refusing while every fresh process reports success — which looks exactly like
a certificate that did not install. Verify with the browser, not with `curl`:

```bash
google-chrome --headless=new --dump-dom https://dev.flagpole.localhost >/dev/null && echo OK
```

Full detail: `docs/walkthrough.md`, and gotcha **#48**.

---

# Appendix B — where to go next

| You want | Read |
|---|---|
| Depth on one mechanism | `docs/claude-code/<mechanism>.md` |
| Why a component exists at all | `docs/decisions/` |
| How each mechanism gets misused | `docs/anti-patterns.md` |
| Where the docs disagreed with reality | `docs/gotchas.md` — 59 rows |
| What actually happened, with output | `docs/walkthrough.md` |
| Rebuild from empty | `docs/BLUEPRINT.md` |
