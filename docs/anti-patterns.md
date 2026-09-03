# Anti-patterns — how each mechanism gets misused (described, never implemented)

For every mechanism: the misuse, why it hurts, and what Flagpole does instead. Pair with `docs/decisions/`.

| Mechanism | The misuse | Why it hurts | What Flagpole does instead |
|---|---|---|---|
| **CLAUDE.md** | A 400-line file with the architecture essay, the API reference, the deploy runbook and "every time you edit Python, run ruff". | Loaded on every request: context cost, diluted attention, contradictions nobody notices, and "always do X" lines that are requests, not guarantees. | 54 lines of facts + names; reference → `api-conventions` skill and `docs/`; procedures → skills; "every time" → hooks. |
| **Managed / user memory** | Putting `flagpole` port numbers in `~/.claude/CLAUDE.md`, or writing org policy ("never force-push") into the managed CLAUDE.md and expecting it to be enforced. | Personal scope leaks project facts to every repo; a managed *CLAUDE.md* is guidance, only managed *settings* enforce. | User example is about the person; `managed-settings.json` carries the deny rules. |
| **Rules** | Ten unconditional rules, three of them about Python with overlapping globs (`**/*.py`, `backend/**`, `**`). | Always-on cost again; overlapping rules contradict; Claude "picks one arbitrarily" (docs). | 3 path-scoped + 1 always-on, one topic each, disjoint globs. |
| **CLAUDE.local.md** | Team conventions ("we use pnpm") hidden in a gitignored file on one laptop. | Teammates and CI never see them; worktrees do not either. | Local file holds only personal sandbox facts; the example says so. |
| **Settings / permissions** | `defaultMode: bypassPermissions` in the shared project settings, or `allow: ["Bash"]`. | Removes every guardrail for everyone who clones the repo; the deny list becomes decoration. | Narrow allow list, 16 denies, `ask` for outward-facing actions; mode left to the user. |
| **Skills** | A skill per Makefile target (`/build`, `/test`, `/lint`), each restating CLAUDE.md, with descriptions like "helps with testing". | Vague, overlapping descriptions make Claude load the wrong one or none; single-line commands do not need a skill. | 5 skills: 3 procedures with real branching, 1 checklist, 1 reference. Descriptions state the trigger. |
| **Subagents** | An agent per task ("api-writer", "test-writer", "doc-writer") with full tool access, spawned for sequential edits the user wants to watch. | Duplicates the main session with less context; edits happen invisibly; no isolation benefit. | 4 agents that exist for isolation (review, audit, verify, browse) with explicit read-only `tools`. |
| **Hooks** | A `type: prompt` Stop hook that asks the model "is the code good?"; a `PreToolUse` hook that rewrites files; a formatter that formats the whole tree; a Stop hook that blocks forever. | Hooks are for deterministic, reasoning-free actions; mutation on PreToolUse races the tool; tree-wide formatting rewrites untouched files; unbounded Stop loops burn the 8-block cap. | 6 hooks, each with a written fail-open/closed decision, tests, `timeout`, touched-file-only formatting, block-once marker. |
| **MCP** | `cluster-status-mcp` wrapping `kubectl get` and `flux get`; an HTTP MCP server binding a port so two sessions can share it; API keys in `.mcp.json`. | Wrapping a CLI adds a process, a schema and a failure mode for data Bash already returns; ports collide; secrets in a committed file. | Cut it (`docs/decisions/cluster-status-mcp.md`); stdio only; `${VAR}` expansion, no secrets. |
| **Plugins** | Packaging this repo's agents/skills/hooks as a plugin "for completeness" while no second repo exists; or duplicating them (plugin *and* `.claude/`). | Two sources of truth; namespaced names (`/flagpole-tools:deploy-local`) confuse the walkthrough; plugin hooks need `/reload-plugins`. | Phase 6 moves (not copies) the components and states the honest trigger: the learning goal. |
| **SDD (Spec Kit)** | A spec for "fix the typo in the README"; running `/speckit-implement` without `/speckit-analyze`; a constitution that lists the build commands; a spec that is updated after the code "to match". | Specs for chores are noise; skipping analyze ships inconsistencies; constitution/CLAUDE.md duplication drifts; a spec that follows code is documentation, not a source of truth. | Chores have decision records, not specs; analyze is a gate; constitution = principles, CLAUDE.md = facts; spec changes first. |

## Feature 005 — platform delivery

| Not built | Why | The signal that would change it |
|---|---|---|
| A database operator | A controller, its custom resources and an upgrade story, to run one database holding a handful of rows. | More than one database, or a real recovery requirement. |
| A second cluster for "production" | The lesson is the overlay boundary, the network policy and the absent grant — all of which are real here. A second control plane adds cost and teaches nothing new. | An actual production deployment, where the control plane boundary stops being decorative. |
| A service mesh | Nothing here needs mutual TLS between three services, and a mesh would double the moving parts a reader has to hold. | Traffic policy or identity between many services. |
| A monitoring stack | `/metrics` exists on every service; scraping it is a separate lesson with its own spec. | Anyone asking a question the logs cannot answer. |
| A registry beside the cluster | `k3d image import` is one command and one fewer component to trust. Feature 006 publishes to ghcr, and the manifests already name the published image. | Images needed by something outside this machine. |
| Backups of the demo database | The cluster is disposable and says so. A backup nobody restores is theatre. | Data anyone would miss. |
| Image automation in Flux | Renovate covers it in feature 006, and two mechanisms updating the same tag is a conflict waiting to happen. | Renovate proving insufficient. |

## Feature 006 — CI and security

| Not built | Why | The signal that would change it |
|---|---|---|
| CodeQL beside semgrep and bandit | Two SAST tools over ~3k lines of Python and TypeScript produce overlapping findings and a longer triage list. That teaches scanning as a volume exercise, which is the opposite of the lesson. One tool per job. | A language neither covers, or a finding class semgrep provably misses. |
| SBOM, provenance and image signing | Right for images other people deploy. Here the output would be an artefact nothing consumes, attached to images only this machine pulls. | The first consumer of these images outside this repository. |
| A Python or Node version matrix | The repository pins one of each and the cluster runs exactly those. A matrix would test configurations that are never deployed and hide the one that is. | Supporting a range, rather than shipping a container. |
| A coverage threshold and a badge | A percentage is not the guarantee the constitution asks for. "Remove the behaviour and exactly one test fails" is, and no number expresses it. | Nothing yet. A badge is decoration. |
| A nightly scheduled scan | The scanners run on every change, and Renovate proposes the updates that fix what they find. A nightly run mostly re-reports yesterday's triage into a channel nobody reads. | Long periods with no commits, where a new CVE could sit unnoticed. |
| A release tool that infers the version | `semantic-release` and friends add a changelog, a tagging step and a bot commit so that a number can be derived from how a commit message was phrased. A person typing one line into `VERSION` is not the hard part of releasing. | Releases frequent enough that typing the number is the bottleneck. |
| `pull_request_target` | It runs the base workflow, with write access, against a fork's code. That is not a trade-off, it is the documented way to hand a stranger your credentials. | Never. |
| A deploy job with a kubeconfig | The credential this entire architecture exists to avoid. Publishing an image is where continuous integration stops; Flux takes it from there. | A cluster Flux cannot reach. |

## Phase 6 — plugin, templates, reproduction

| Not built | Why | The signal that would change it |
|---|---|---|
| A second plugin | One is enough to show the mechanism, and the first one is already hard to justify for a single repository. | A genuinely separable set of components with a different audience. |
| Hooks inside the plugin | A plugin can be disabled with one command. Enforcement that can be switched off is a suggestion, so both guards stayed in `.claude/settings.json` next to `permissions.deny`. | Never — if a guard must travel between repositories, it travels as a *copied* settings block, not as something optional. |
| Publishing the plugin to a remote marketplace | The marketplace is this repository. Publishing adds a release process for an artefact with one consumer, which is this repository. | A second repository that needs these components. |
| Keeping the components in `.claude/` **and** in the plugin | Two sources of truth. The first edit to one makes the other a lie, and nothing would catch it. `scripts/check-blueprint.sh` asserts the `.claude/` copies are gone. | Never. |
| Templates generated from the live files | A generator would keep them in sync and lose the only thing that makes them worth having — the comment saying *when not to* reach for the mechanism. | Templates drifting far enough that someone copies a broken one. |
| Re-running the whole rebuild end to end | It needs an empty machine, a new GitHub repository, `flux bootstrap` and a cluster. Claiming to have re-run it would be the kind of unverified statement this repository exists to avoid. | Someone actually doing it — the blueprint names the three steps that were not re-run. |
