# <PROJECT> — Claude Code learning demo (generic prompt)

> **How to use:** paste as the first message in a fresh Claude Code session at the root of an empty
> repository. Replace every `<PLACEHOLDER>`. Confirm the **Decisions** table (section 3) before any
> file is written.

This is the de-projected version of the prompt that produced Flagpole. Sections 2, 6, 7 and 9 are
unchanged, because they are the part that transfers; sections 1, 3, 4, 5 and 8 are where your project
goes.

Ultrathink every step. Use plan mode for Phases 0–1. Do not write files until the plan is approved.

---

## 1. Goal

I am learning Claude Code. The deliverable is a **small, professional, fully working demo app** whose
real purpose is to teach me — by example and by documentation — **when, where, and how far** to use
each Claude Code extension mechanism, using only **official, current** configuration, and to do it
through **Spec-Driven Development** so that specs, not chat, drive the code.

Four outcomes, in priority order:

1. **Judgment.** For every mechanism (memory scopes, rules, settings/permissions, skills, subagents,
   hooks, MCP, plugins) I must come away knowing: the problem it solves, the trigger that justifies
   adding it, the cheaper alternative it competes with, how far to take it, and the failure mode of
   overusing it.
2. **SDD discipline.** Every feature goes constitution → spec → clarify → plan → tasks → analyze →
   implement. I must see how a spec toolkit plugs into Claude Code and how it relates to CLAUDE.md,
   rules and skills **without duplicating them**.
3. **A correct, reproducible reference implementation** of each mechanism, each justified by a real
   need in this repository — never added "because the feature exists."
4. **A working app** spanning <the stack you want to exercise: e.g. a frontend, a backend, containers,
   deployment, CI, secrets, dependency automation, authentication>.

Complexity budget goes to clarity and correct usage, not to app features. **Restraint is part of the
lesson:** the docs must show what was deliberately *not* built and why.

---

## 2. Usage doctrine (apply this to every component you add)

Base this on the official page "Extend Claude Code" (`code.claude.com/docs/en/features-overview`) and
the Anthropic blog post "Steering Claude Code" it links to. Fetch both. Then apply the rules below;
where the docs and my rules differ, **follow the docs and flag it in `docs/gotchas.md`**.

### 2.1 The decision test (run it before creating any component)

1. **Can the built-in tools + a one-line CLAUDE.md instruction do this?** If yes, stop there.
2. **Is it always-on context or on-demand?** Always-on → CLAUDE.md or rule. On-demand → skill.
3. **Does it need to hold every time regardless of what Claude decides?** → hook (or `permissions.deny` if it is a plain allow/deny). An instruction is a request; a hook is enforcement.
4. **Does it need context isolation, parallelism, or would it flood the main conversation?** → subagent.
5. **Does Claude need data or actions from a system it cannot reach through the shell?** → MCP. If a CLI already exists (the CLIs your project already uses), prefer Bash + a skill over a new MCP server.
6. **Will a second repo need the identical setup?** → plugin. Otherwise keep it in `.claude/`.
7. **Is this a feature (user-visible behavior) or a chore (tooling/config)?** Features go through SDD (section 2.5). Chores do not get a spec.

Record the answer for each component in a short decision record (see 2.3).

### 2.2 Per-mechanism rules: use / don't / how far

| Mechanism | Use it when | Do NOT use it for | How far (a sane starting budget) | Overuse smell |
|---|---|---|---|---|
| **CLAUDE.md (project)** | Facts every session needs: build/test commands, layout, conventions, "always/never" rules. Trigger: Claude got it wrong twice. | Reference docs, procedures, anything derivable from the code, anything only relevant to a subtree, product principles (those live in the SDD constitution). | < 150 lines. Specific and verifiable. Points to the constitution and `specs/`; does not restate them. | Long prose, architecture essays, duplicated README/constitution content, contradictory rules. |
| **User / managed memory** | Personal preferences (user); org-wide policy that must not be excluded (managed). | Project-specific facts. | One short example each; ship as templates + installer. | Project rules leaking into user scope; managed file used for guidance that should be enforced via managed settings. |
| **Rules `.claude/rules/`** | Topic-specific conventions; path-scoped guidance that should load only when touching matching files. | Whole-project "always" rules; procedures. | 3–5 files. ≥ 2 path-scoped. One topic per file. | Many unconditional rules; overlapping globs. |
| **CLAUDE.local.md** | Personal per-project overrides (sandbox URLs, test data). | Anything a teammate needs. | Example file only; real file gitignored. Explain the worktree caveat and the `@~/...` import alternative. | Team conventions hidden in a local file. |
| **Settings / permissions** | Hard allow/deny/ask on tools and paths; hook registration; enabling plugins. | Behavioral guidance. | Allow list limited to the workflow; deny destructive git/kubectl/rm patterns; explain precedence. | `bypassPermissions` as a habit; allow lists that grant everything. |
| **Skills** | Repeatable multi-step procedures you'd otherwise paste, or reference material Claude needs sometimes. Trigger: pasted the same playbook 3 times. | Always-on rules; single-line commands; enforcement; re-implementing what Spec Kit already provides. | 3–5 of your own, plus whatever a spec toolkit installs. Precise `description`; `disable-model-invocation: true` on skills with side effects. | Skills that restate CLAUDE.md; vague overlapping descriptions; a skill per make target. |
| **Subagents** | Work that reads many files and returns a summary; parallel independent tasks; a reviewer that must not edit; a restricted tool set. | Ordinary sequential edits; anything the main session must see step by step. | 3–4 agents, each with explicit `tools` and a one-paragraph system prompt. Read-only for reviewers/auditors. | Agents that duplicate the main session; full tool access; agent per task. |
| **Hooks** | Things that must happen *every* time and need no reasoning: format after edit, block unsafe commands, log, notify, inject environment facts at session start. | Anything needing judgment; long-running work; substitutes for tests/CI; nagging. | See 2.4. ≤ 6 hooks; each justified by "a CLAUDE.md line was not sufficient because…". | Hooks calling the model; repo mutation on `PreToolUse`; looping `Stop` hooks; output flooding context. |
| **MCP servers** | External systems Claude can't reach via shell, or a browser (Playwright). Also to *learn* how to build one — state that honestly. | Wrapping a CLI that works from Bash; tool sprawl. | 1 official + at most 2 custom. stdio by default. Each tool must be used in the walkthrough. | Secrets in `.mcp.json`; HTTP servers binding ports for no reason. |
| **Plugins** | Reusing the same setup across repos or distributing it. | A single repo. | Last phase, if at all; the same components **moved**, never copied. | Plugin "for completeness". |
| **SDD (Spec Kit)** | Any user-visible feature or behavior change; anything with acceptance criteria. Trigger: you would otherwise explain requirements in chat. | Tooling chores (hooks, CI YAML, formatter config), one-line fixes. | One spec per feature, one feature branch each; analyze before implement, every time. | Specs for trivial changes; spec and code drifting apart; constitution duplicating CLAUDE.md. |

### 2.3 Decision records (mandatory)

For every component created, add `docs/decisions/<component>.md` (≤ 20 lines):

- Problem it solves in *this* repo (concrete trigger) and the spec ID it serves, if any.
- Alternative considered and rejected (e.g. "a CLAUDE.md line" / "a Bash command in a skill" / "no hook, rely on CI").
- Limits applied (scope, tools, matcher, `if`, timeout, size).
- What was deliberately **not** done, and the signal that would justify doing it later.
- Verification: the command/output proving it loaded and fired (`/context`, `/hooks`, `/mcp`, `/agents`, `InstructionsLoaded` log).

Also produce `docs/anti-patterns.md`: for each mechanism (including SDD), one short "how people misuse this" example, described, not implemented.

### 2.4 Hook hard rules (hooks are the sharpest tool — handle accordingly)

- Prefer `permissions.deny` for plain blocks; use a `PreToolUse` hook only when the rule needs to inspect content or arguments.
- Every hook: exec form (`command` + `args`), `${CLAUDE_PROJECT_DIR}` paths, narrow `matcher` + `if`, explicit `timeout` (≤ 10 s for tool events), deterministic, idempotent, no network, no LLM calls (`type: prompt/agent` hooks are documented but not enabled by default).
- Fail-open vs fail-closed is a written decision per hook. Enforcement hooks use exit 2 or `permissionDecision: deny`; never rely on exit 1.
- Hooks never mutate tracked files except formatters on `PostToolUse` for the touched file only.
- Hook stdout is context: return `additionalContext` only when Claude must act on it; log everything else to `.claude/logs/` (gitignored).
- A `Stop` hook may block at most once per turn (marker file) to avoid loops.
- Each hook has a shell test under `.claude/hooks/tests/` fed with sample stdin JSON, run by `make test-hooks`.
- Document exit-code semantics, JSON output fields, scopes, merge behavior, and `/hooks`.

### 2.5 Spec-Driven Development rules

Tool: **GitHub Spec Kit** (`github.com/github/spec-kit`, official, MIT). Read its README, installation guide, and the Claude Code integration notes before installing. Verify the current flag names (`--integration claude` in recent versions, `--ai claude` in older ones) and the current release tag; do not guess.

- Install pinned: `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@<latest-tag>`; then `specify init --here --integration claude --script sh`. Inspect what it wrote into `.claude/` (commands/skills) and `.specify/` and document it in `docs/claude-code/sdd.md` — this is the lesson on how third-party tooling extends Claude Code.
- Workflow per feature, on a branch named by Spec Kit (`001-…`): `/speckit.constitution` (once) → `/speckit.specify` → `/speckit.clarify` → `/speckit.plan` → `/speckit.tasks` → `/speckit.analyze` → `/speckit.implement`. Use `/speckit.checklist` where acceptance criteria are fuzzy.
- **Constitution vs CLAUDE.md:** the constitution holds product and engineering principles and non-negotiables that the SDD gates check (testing policy, simplicity, security baseline, "no plaintext secrets"). CLAUDE.md holds operational facts (commands, layout, conventions) and links to the constitution. Neither restates the other.
- **Spec is the source of truth.** Code, tests, manifests, and decision records reference the spec ID. If implementation reveals the spec was wrong, update the spec first, then the code.
- Features (≤ 6): `001-flagpole-api`, `002-flagpole-web`, `003-flagpole-consumer`, `004-flagpole-mcp`, `005-platform-delivery` (containers, Kubernetes, Flux, secrets, auth), `006-ci-and-security`. Claude Code scaffolding (Phase 2) is a chore, not a feature — no spec.
- `[CONFIRM]` Fallback if Spec Kit is rejected: a lightweight `specs/<nnn>-<name>/{spec,plan,tasks}.md` with the same gates, driven by our own `/spec` skill.

---

---

## 3. Decisions — confirm or override before starting

Mark every row you want to be asked about `[CONFIRM]`. Ask them all in **one** message.

| Area | Proposal | |
|---|---|---|
| App | <what it does, in one sentence> | `[CONFIRM]` |
| Language / framework | <backend>, <frontend> | |
| Spec toolkit | <name and exact version, pinned> | `[CONFIRM]` |
| Deployment target | <local cluster? a PaaS? nothing?> | `[CONFIRM]` |
| Secrets | <how they are stored and decrypted> | |
| CI and registry | <provider, where images or artifacts go> | |
| Auth | <identity provider, roles> | |
| Plugin | <build one in the last phase, or state honestly why not> | `[CONFIRM]` |
| Repository | <new? public or private? who owns it?> | `[CONFIRM]` |
| `sudo` | Never run by you. Print the command; I run it. | |

---

## 4. The demo app

### 4.0 Naming (use these exactly)

<Every service, image, namespace, host and seeded record, spelled once. This section prevents more
rework than any other: if a name is ambiguous, it will be guessed consistently and wrongly.>

### 4.1 <App name>

<What it does, in the smallest form that still needs the mechanisms you want to learn. Two or three
entities. One rule that is worth testing. Resist every feature that does not force a new mechanism.>

### 4.2 Platform requirements

<Ports, hosts, what must run locally, what must never run without being asked.>

### 4.3 Alternatives to present when asking for confirmation

<For each `[CONFIRM]` row, the option you would pick and the one you would not, with the reason.>

---

## 5. Claude Code components to implement

One per mechanism, each passing the decision test in 2.1 and each with a decision record:

- **Memory** — project `CLAUDE.md` (< 150 lines, one import), a `CLAUDE.local.md.example`, and short
  user/managed examples shipped as templates with an installer that *prints* any `sudo` command.
- **Rules** — 3–5 files, at least two path-scoped, one topic each.
- **Settings and permissions** — an allow list limited to the workflow, a deny list covering the
  destructive shapes, an ask list for anything that reaches outside the repository.
- **Subagents** — 3–4, each read-only unless it has a reason not to be, each with explicit `tools`.
- **Skills** — 3–5 of your own; `disable-model-invocation: true` on anything with side effects.
- **Hooks** — at most 6, each justified by "a CLAUDE.md line was not sufficient because…". At least
  one must inspect *content*, which is the case a permission rule cannot express.
- **MCP** — one official server, and at most one you write yourself. If a CLI already returns the
  data, say so and use Bash instead.
- **Plugin** — only if a second repository will need this setup. If you build one anyway to learn the
  mechanism, say that in the decision record rather than inventing a need.
- **Reference-only** — one paragraph each for the mechanisms you deliberately did not use.

---

## 6. Process

1. **Phase 0 — Discovery (plan mode).** Fetch the Claude Code docs index and every relevant page;
   fetch the docs for every tool you will rely on. Ask all `[CONFIRM]` questions in one message.
   Check host prerequisites; report gaps; never install system packages without asking.
2. **Phase 1 — Plan.** Directory tree; component list with its doc page and decision-test answer;
   feature list; port table; phase order. Wait for approval.
3. **Phase 2 — Scaffolding (chores, no spec).** Memory, rules, settings, hooks, agents, skills,
   `.mcp.json`; initialise the spec toolkit; write the constitution. Verify with `/context`,
   `/hooks`, `/mcp`, `/agents`, `/memory` before any feature work. Write decision records as you go.
4. **Phase 3 — The features, via the SDD loop.** For each: specify → clarify (ask me) → plan → tasks
   → analyze → implement → review → merge.
5. **Phase 4 — Delivery.** <Containers, deployment, secrets — whatever "it runs somewhere real" means
   for this project.> Prove it by running it, not by describing it.
6. **Phase 5 — CI and the security gate.** Every change checked; dependency updates proposed
   automatically; every scanner finding either fixed or recorded with a decision, a reason and a date.
7. **Phase 6 — Plugin (if confirmed), docs, and reproduction.** Run `docs/BLUEPRINT.md` from scratch
   in an empty directory and confirm it reproduces.

Working rules: conventional commits per task; one feature branch per spec; never commit secrets,
`CLAUDE.local.md`, `settings.local.json`, or logs. **Verify every claim by running it and showing the
output.** Docs beat memory. If something cannot be done honestly, stop and present options. Fewer,
clearer components beat exhaustive ones.

---

## 7. Sourcing rules

Allowed: `code.claude.com/docs`, `docs.claude.com`, `github.com/anthropics/*`, `github.com/modelcontextprotocol/*`, `github.com/microsoft/playwright-mcp`, `github.com/github/spec-kit`, the official documentation of every tool you actually use, official Docker images and Helm charts, upstream-maintained PyPI/npm packages.
Not allowed: "awesome" lists, blog snippets, unmaintained packages. Every dependency: maintained, pinned, scanned, listed with a one-line justification in `docs/dependencies.md`.

---

---

## 8. Deliverables checklist

- [ ] `README.md`: purpose, quickstart, an architecture diagram, and a map *mechanism → file →
      decision record → doc link*, plus *spec → code → tests* traceability.
- [ ] `docs/claude-code/<mechanism>.md` for each: what / where / when / how far / our implementation /
      how to verify it loaded / common mistakes.
- [ ] The spec toolkit's directory, with the constitution and a spec/plan/tasks per feature, all
      reconciled with the code.
- [ ] `docs/decisions/*.md` — one per component.
- [ ] `docs/anti-patterns.md` (what was deliberately not built, and the signal that would change it)
      and `docs/gotchas.md` (what the docs say versus what actually happened).
- [ ] `docs/BLUEPRINT.md` — rebuild from an empty folder, including the exact prompts per step.
- [ ] `templates/` — copy-ready versions of every mechanism, plus a generic version of this prompt.
- [ ] `docs/walkthrough.md` — every hook, agent, skill and MCP tool shown once **with real output**.
- [ ] <Your project's operational docs: ports, dependencies, security findings, secret handling.>
- [ ] The quickstart commands green on a clean machine.

---

## 9. Mandatory constraints

- Do not omit, skip, or silently assume any item in sections 2, 4, 5 and 8. If an item is impossible
  or unwise, say so and propose the alternative.
- Every component passes the decision test (2.1) and has a decision record. A component without a
  concrete trigger in this repository is not built — it is described in `docs/anti-patterns.md`.
- No feature code without a spec, a plan and tasks that passed the analyze gate.
- Simple, modular, pragmatic. The app is a vehicle; resist feature creep.
- All packages, images and manifests pass the scanners; exceptions documented with a reason and a date.
- No port collisions: check before binding.
- Batch questions; ask whenever a decision is not covered here.

---

## 10. The two rules the original run kept re-learning

Neither was in the prompt that produced Flagpole. Both were paid for in rework, so they are here now:

1. **A check that has never failed has not been tested.** Every guard, hook, contract assertion and
   CI job gets broken on purpose once, watched going red, and put back. Three separate checks in that
   project passed for the wrong reason — one of them could never have failed at all.
2. **Enforcement does not belong anywhere it can be switched off.** Not in prose, not in a plugin.
   A guard lives in `settings.json` next to `permissions.deny`, or it is a suggestion.
