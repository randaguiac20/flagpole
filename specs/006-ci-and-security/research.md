# Research: ci-and-security

Every version and digest below was resolved by running the command shown, on 2026-09-02. None is
copied from memory: a fabricated digest is the one kind of error that looks correct in review and
fails only in the runner.

## E1 — Which provider runs the checks

**Decision**: GitHub Actions.

**Rationale**: the repository already lives on GitHub, the registry is `ghcr.io` under the same
account, and the publishing job can authenticate with the token the runner is given rather than one
stored anywhere. A second provider would mean a second credential and a second place to look when a
check fails.

**Alternatives**: a self-hosted runner (nothing here needs one, and it would be a machine to keep
patched); running the checks only in pre-commit (a hook can be skipped with `--no-verify`, so it is a
convenience, not a gate).

## E2 — Pinning the actions

**Decision**: every `uses:` names a commit SHA with the tag in a trailing comment. Resolved:

```
$ gh api repos/<a>/releases/latest --jq .tag_name
$ gh api repos/<a>/git/ref/tags/<tag> --jq .object.sha
actions/checkout             v7.0.1     3d3c42e5aac5ba805825da76410c181273ba90b1
actions/setup-node           v7.0.0     820762786026740c76f36085b0efc47a31fe5020
astral-sh/setup-uv           v10.0.1    20cfd1bf945f4377ade1205e4dbc17946fc9a30d
docker/setup-buildx-action   v4.3.0     37fe631027851001ddb9b187196cc803df7f5f0e
docker/login-action          v4.6.0     dbcb813823bdd20940b903addbd779551569679f
docker/build-push-action     v7.3.0     53b7df96c91f9c12dcc8a07bcb9ccacbed38856a
docker/metadata-action       v6.2.0     dc802804100637a589fabce1cb79ff13a1411302
```

**Rationale**: `uses: actions/checkout@v7` is a moving reference to code that runs with the
repository checked out and, in the publishing job, with a token that can write packages. A tag can be
repointed. FR-011 asks for reproducibility; this is also the same argument feature 005 made for image
digests, applied to the other kind of dependency this repository consumes.

**Alternatives**: floating tags (the diff would show nothing when the code changed); a fork of each
action (a maintenance burden with no benefit once the SHA is pinned).

## E3 — The publishing credential

**Decision**: the automatic `GITHUB_TOKEN`, with `permissions:` set per workflow. `ci.yml` declares
`contents: read` and nothing else; `release.yml` declares `contents: read` and `packages: write` on
the publishing job only.

**Rationale**: no credential is stored, rotated or leaked, because there is none to store. GitHub
mints a token scoped to the run, and the default for `permissions:` at workflow level replaces the
repository-wide default, so the scope is visible in the file rather than in a settings page.

**Alternatives**: a personal access token in a repository secret (a long-lived credential that
outlives the run and can be printed by any step); trusted publishing / OIDC to an external registry
(right answer for PyPI or a cloud registry, unnecessary for ghcr on the same account).

**Trap worth naming**: pushing a file under `.github/workflows/` over **HTTPS** with a token that
lacks the `workflow` scope is refused. This repository's remote is SSH
(`git@github.com:randaguiac20/flagpole.git`), so the push uses the SSH key and the scope does not
apply — `gh auth status` here reports `gist, read:org, repo` and no `workflow`. Anyone reproducing
this over HTTPS needs to add that scope. → gotcha.

## E4 — What runs when

**Decision**:

| Workflow | Trigger | Runs |
|---|---|---|
| `ci.yml` | `pull_request`, and `push` to `main` | lint, backend/consumer/mcp/frontend tests, hook tests, scanners |
| `release.yml` | `push` to `main`, only when a build input changed | build and publish three images |

Documentation-only changes are excluded with `paths-ignore` on `release.yml` (`docs/**`, `specs/**`,
`**/*.md`). `ci.yml` deliberately has **no** path filter: a change to a rule, a hook or a spec should
still see the lint and hook tests run.

**Rationale**: FR-004 wants a documentation change not to trigger a build. Path filters express that
in the trigger, where it can be read, rather than in a condition on each job. Both workflows set
`concurrency: {group: <workflow>-<ref>, cancel-in-progress: true}` so a second push supersedes the
first rather than queueing behind it.

**Alternatives**: `paths` (allow-list) on `ci.yml` — rejected, because the failure mode is silent:
a new directory nobody added to the list is simply never checked.

## E5 — Fork safety

**Decision**: `pull_request` only, never `pull_request_target`, and no secret is referenced by any
job that a fork's change can reach.

**Rationale**: `pull_request_target` runs the *base* workflow with a token that has write access,
while checking out the *fork's* code — which is how a change from outside the repository gets to run
with the repository's credentials. `pull_request` gives a fork a read-only token and no secrets.
FR-014 is asserted rather than assumed: the contract check fails if either workflow names
`pull_request_target` or references `secrets.` outside the publishing job.

**Alternatives**: none seriously considered; this is the documented failure and the reason the
distinction exists.

## E6 — The scanner set and what a finding does

**Decision**: `scripts/scan.sh` runs all eight, does not stop at the first, and reports a summary
table at the end. Versions present on this machine, and pinned in CI:

```
$ trivy --version | head -1   → 0.74.0
$ hadolint --version          → 2.15.1
$ osv-scanner --version       → 2.5.1
$ gitleaks version            → 8.30.1
$ semgrep --version           → 1.176.0
$ bandit --version            → 1.9.4
$ pip-audit --version         → 2.10.1
npm audit ships with npm
```

Failure policy, per FR-009 and FR-012:

| Scanner | Fails the run on |
|---|---|
| gitleaks | any finding — a leaked credential is never a judgement call |
| hadolint | any finding at `error` |
| bandit, semgrep | any finding at `HIGH` |
| pip-audit, npm audit, osv-scanner, trivy | any vulnerability at `HIGH` or `CRITICAL` |

A finding below those thresholds is reported and does not fail. A finding at or above them fails
until it is written into `docs/security-findings.md` with a decision — which is what makes the
document the only way past a scanner, rather than a place to file things nobody reads.

**Rationale**: `set -e` and eight scanners means the first finding hides the other seven. Collecting
all of them and failing once at the end is the difference between one fix per run and one run per
fix.

**Alternatives**: per-scanner suppression files (eight formats, eight places to look, and the reason
sits next to the rule instead of next to the risk); failing on everything including `LOW` (the demo
would stop on a transitive `LOW` in a dev-only dependency and teach that the answer is to disable
the scanner).

## E7 — Version and tags

**Decision**: a `VERSION` file at the repository root holding a semver line, changed by a person in
the change that earns it. `release.yml` reads it and publishes each image twice:
`ghcr.io/randaguiac20/flagpole-<svc>:<VERSION>` and `:sha-<short commit>`.

**Rationale**: the user's clarification, recorded in the spec. The version becomes a reviewable line
in a diff rather than an inference from commit wording, and the commit tag means every published
image can be traced to the source that built it even when the version has not moved.

**Guard**: publishing a version that already exists in the registry would silently move a tag other
people may have pulled. `release.yml` checks first and fails with the instruction to bump `VERSION`.

**Alternatives**: `semantic-release` or `release-please` (a tool, a changelog, a tagging step and a
bot commit, to decide a number a person can type); `latest` (the tag feature 005 spent effort
avoiding); git tags as the source (the version would live outside the tree that Renovate reads).

## E8 — Renovate configuration

**Decision**: `renovate.json` at the root, `"extends": ["config:recommended"]`, with explicit
managers for every kind of pin this repository introduced:

| Manager | What it updates here | Note |
|---|---|---|
| `pep621` / `uv` | `backend`, `consumer`, `mcp/flagpole-mcp` | uv lockfiles maintained |
| `npm` | `frontend` | lockfile maintained |
| `dockerfile` | the three Dockerfiles | **digest pinning kept** — `pinDigests: true` |
| `github-actions` | both workflows | SHA pins, with the tag comment kept in step |
| `pre-commit` | `.pre-commit-config.yaml` | **off by default** — enabled explicitly |
| `helm-values` / `flux` | `platform/*/release.yaml` | chart versions |
| `kubernetes` | `deploy/**` image tags | needs `managerFilePatterns` |

**Rationale**: the point of feature 005 was that everything is pinned; the point of this feature is
that a pin has a way of moving that a person reviews. A manager that is off silently is a set of pins
nobody is watching.

**Key names**: the configuration key is **`managerFilePatterns`**, not `fileMatch` (renamed in
Renovate 41) — recorded as gotcha #7 during discovery. Checked while implementing T019, and the
discovery note was half right: `renovate-config-validator` does **not** refuse `fileMatch`. It prints
`WARN: Config migration necessary`, shows the migration diff, and **exits 0**:

```
$ npx --yes --package renovate -- renovate-config-validator renovate-with-filematch.json
 WARN: Config migration necessary
 WARN: Config migration diff:
 INFO: Config validated successfully against 1 file(s)
$ echo $?
0
```

So a deprecated key would pass CI silently. Two consequences: `scripts/check-ci-contract.sh` asserts
the key is absent, and the lint job treats "migration necessary" in the validator's output as a
failure rather than reading the exit status.

**Grouping**: non-major updates for each ecosystem are grouped into one change per week
(`schedule: ["before 6am on monday"]`, `prConcurrentLimit: 3`) so the repository proposes a handful
of reviewable changes rather than thirty. Major updates arrive separately, ungrouped — a major is a
decision, not a bump.

**Delivery**: the Mend-hosted GitHub App, installed on the repository by the user. Nothing in this
repository holds a token for it, and there is no scheduled workflow running Renovate itself.

**Alternatives**: Dependabot (no `pre-commit` or Helm manager, no grouping across ecosystems, and a
second file to configure — it is genuinely simpler, and if this repository had only npm and Actions
it would be the right choice; recorded in the decision record rather than dismissed); self-hosted
Renovate in a scheduled workflow (a token with write access on a schedule, for a demo).

## E9 — Where the pipeline stops

**Decision**: continuous integration ends at a published image. It never touches the cluster.

**Rationale**: feature 005 established that the cluster changes when a manifest is merged, and that
`kubectl apply` into a `flagpole-*` namespace is refused by a hook. A deployment step here would
contradict both. The path is: publish → Renovate sees the newer tag → proposes the bump in
`deploy/` → merge → Flux reconciles.

**Alternatives**: a deploy job with a kubeconfig secret (the credential this architecture exists to
avoid); Flux image automation (it would write the tag itself, which is the same job Renovate is
already doing for six other kinds of dependency — one mechanism, not two; recorded in
`docs/anti-patterns.md`).

## E10 — Deliberately not built

| Not built | Why not |
|---|---|
| CodeQL / any SAST beyond semgrep + bandit | `github/codeql-action` is real (`codeql-bundle-v2.26.4`) and would work. Two SAST tools on ~3k lines of Python and TypeScript would produce overlapping findings and a longer triage list, teaching that scanning is a volume exercise. One is the lesson. |
| SBOM and provenance attestation | Right for software other people deploy. Here it would add a step whose output nothing consumes. Named as the signal for when it becomes right: the first external consumer of these images. |
| Image signing (cosign) | Same reasoning, plus a key to manage. Flux can verify signatures; nothing here is asking it to. |
| A test matrix over Python or Node versions | The repository pins one of each, deliberately, and the cluster runs exactly those. A matrix would test configurations that are never deployed. |
| Coverage thresholds and a badge | A percentage is not the guarantee the constitution asks for; the mutation habit (remove the behaviour, exactly one test must fail) is. |
| A scheduled nightly scan | The scanners run on every change, and Renovate proposes the updates that fix findings. A nightly run would mostly re-report yesterday's triage. |
| `pull_request_target` | See E5. |
