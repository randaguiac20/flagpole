# Tasks: ci-and-security

**Input**: Design documents from `/specs/006-ci-and-security/`

**Tests**: requested — the constitution requires a failing check before the behaviour exists. Here
the checks are `scripts/check-ci-contract.sh` and `actionlint` over the workflows, plus the
deliberate breakages in `quickstart.md`; a workflow that has never failed has not been tested.

**Organization**: by user story, so each is independently completable and testable.

## Phase 1: Setup

- [ ] T001 Write `scripts/check-ci-contract.sh` reading `contracts/ci-contract.json` — triggers, `permissions`, jobs, action SHA pins, forbidden patterns, `VERSION` shape, Renovate managers, findings columns. Run it now, against a repository with no workflows, and show it failing
- [ ] T002 [P] Install `actionlint` (`mise use -g actionlint`) and add it, with `renovate-config-validator` via `npx`, to the tool list in `docs/BLUEPRINT.md`
- [ ] T003 [P] Create `VERSION` holding `0.1.0`; make `scripts/build.sh` and `.env.example` read it instead of hardcoding `FLAGPOLE_IMAGE_TAG` (FR-005a — nothing writes this file)
- [ ] T004 [P] Create `docs/security-findings.md` with the seven columns from `data-model.md`, the failing thresholds from research E6, and the rule that a row is never deleted

## Phase 2: Foundational (blocking prerequisites)

- [ ] T005 Implement `scripts/scan.sh`: all eight scanners, **no early exit**, a summary table at the end, and a missing tool treated as a failure rather than a skip (FR-010, FR-011)
- [ ] T006 Prove `scan.sh` bites: plant a credential in a Python file, run `make scan`, show the gitleaks finding and the non-zero exit; then rename a scanner off `PATH` and show FR-011 — "not installed" fails, it does not pass quietly. Remove both
- [ ] T007 Run `make scan` for real and record **every** finding at or above its threshold in `docs/security-findings.md` with a decision, a reason and today's date. Fix what is fixable rather than accepting it
- [ ] T008 Make `scan.sh` consult `docs/security-findings.md`: a recorded finding no longer fails the run, an unrecorded one does. This is what makes the document load-bearing instead of decorative (FR-012)

## Phase 3: User Story 1 — every change is checked before anyone looks at it (P1)

**Goal**: a change cannot reach `main` with a failing test, a lint error or an unrecorded finding,
and the failure is visible on the change itself.

**Independent test**: open a change that breaks a test; the check fails and names it.

- [ ] T009 [US1] Write `.github/workflows/ci.yml`: triggers `pull_request` and `push` to `main`, `permissions: {contents: read}`, a concurrency group that cancels superseded runs, every `uses:` pinned to the SHA recorded in research E2 with its tag in a comment
- [ ] T010 [P] [US1] Add jobs `test-backend`, `test-consumer`, `test-mcp` — `astral-sh/setup-uv`, `uv sync --frozen`, `uv run pytest`; the lockfile is honoured, not refreshed
- [ ] T011 [P] [US1] Add job `test-frontend` — `actions/setup-node` with the Node version the image uses, `npm ci`, `npm test`
- [ ] T012 [P] [US1] Add job `lint` — `ruff check`, `ruff format --check`, `shellcheck`, `actionlint`, `scripts/check-image-pins.sh`, `scripts/check-ci-contract.sh`
- [ ] T013 [P] [US1] Add job `test-hooks` — `make test-hooks`, so the mechanisms that guard this repository are themselves checked (FR-001)
- [ ] T014 [US1] Add job `scan` — `make scan`, the same command as locally, so the local and automated runs cannot drift (FR-013)
- [ ] T015 [US1] Run `actionlint .github/workflows/ci.yml` and `scripts/check-ci-contract.sh`; both must pass. Then flip `pull_request` to `pull_request_target` and show the contract check failing and naming FR-007, and put it back
- [ ] T016 [US1] Push the branch, open the change, and show every job green (`gh pr checks --watch`)
- [ ] T016a [US1] Prove FR-006: show `scripts/check-ci-contract.sh` refusing a workflow that names `kubectl` or a kubeconfig secret — continuous integration stops at a published image and never writes to the cluster
- [ ] T016b [US1] Measure SC-002: `gh run list --json databaseId,createdAt,updatedAt` for the last run, and record the wall-clock time. Under 10 minutes, or split a job — do not raise the budget
- [ ] T017 [US1] Prove SC-001: break one backend assertion, push, show `test-backend` red on the change, revert

## Phase 4: User Story 2 — dependencies are proposed, not chased (P1)

**Goal**: every kind of pin this repository introduced has a mechanism that proposes its update, and
a merged proposal reaches the cluster with no manual step.

**Independent test**: merge one update proposal; `flux reconcile` and `verify-cluster.sh` still pass.

- [ ] T018 [US2] Write `renovate.json`: `config:recommended`, the eight managers from research E8, `pinDigests: true`, grouping by ecosystem, `prConcurrentLimit: 3`, `automerge: false` everywhere. Use `managerFilePatterns` — `fileMatch` is rejected by the validator (gotcha #7)
- [ ] T019 [US2] Validate it: `npx --yes --package renovate -- renovate-config-validator renovate.json`, and show the output. Then plant a `fileMatch` key and show the validator refusing it, so the CI step is known to bite
- [ ] T020 [US2] Write `.github/workflows/release.yml`: `push` to `main` with `paths-ignore` for `docs/**`, `specs/**` and `**/*.md`; `permissions: {contents: read, packages: write}` on the `publish` job alone; build and push the three images tagged with `VERSION` and `sha-<short commit>`, with OCI revision/source labels
- [ ] T021 [US2] Add the republish guard: before building, query the registry for the tag in `VERSION` and fail with "bump VERSION" rather than moving a tag someone may have pulled (research E7)
- [ ] T022 [US2] Prove FR-004: push a documentation-only commit and show `gh run list` — a `ci` run and no `release` run
- [ ] T023 [US2] Merge to `main`, watch `release.yml`, and show both tags on `flagpole-api` in the registry plus the `org.opencontainers.image.revision` label matching the commit (SC-004)
- [ ] T024 [US2] Write `docs/renovate.md`: what each manager covers, why `pre-commit` and `kubernetes` must be enabled explicitly, how the grouping is chosen, and what stays pinned by hand and why
- [ ] T025 [US2] **User action**: install the Mend Renovate app on `randaguiac20/flagpole` (an account action Claude cannot take). Then show the Dependency Dashboard issue and the first proposals
- [ ] T026 [US2] Take one proposal through to the cluster: review, merge, `flux reconcile kustomization flagpole-dev --with-source`, `scripts/verify-cluster.sh` — 43 passed, 0 failed (SC-005)

## Phase 5: User Story 3 — findings are triaged, not accumulated (P2)

**Goal**: every finding has a decision and a date, and nothing can be ignored by being left alone.

**Independent test**: `make scan` exits 0, and every finding it reported has a row.

- [ ] T027 [US3] Reconcile `docs/security-findings.md` against a fresh `make scan`: no row without a finding, no finding without a row (SC-006)
- [ ] T028 [US3] Prove SC-007: run `make scan` locally and compare its findings with the `scan` job's output for the same commit; they must agree, and if they do not, say which is right and why
- [ ] T029 [US3] Prove FR-014 and SC-008: download the full log of the most recent run and run `gitleaks detect --no-git` over it, plus a grep for `ghp_`, `gho_`, `github_pat_`, private-key headers and `age1…`. Expect nothing
- [ ] T030 [US3] Add a `deferred` example with a condition that ends it, so the format shows what an honest deferral looks like — or, if nothing is genuinely deferred, say so rather than inventing one

## Phase 6: Polish & cross-cutting

- [ ] T031 [P] Decision record `docs/decisions/ci-github-actions.md` — trigger, alternatives (self-hosted runner, pre-commit only), limits
- [ ] T032 [P] Decision record `docs/decisions/dependency-updates-renovate.md` — including the honest note that Dependabot would suffice for a repository with only npm and Actions
- [ ] T033 [P] Decision record `docs/decisions/versioning.md` — the `VERSION` file, and why no release tool
- [ ] T034 [P] Decision record `docs/decisions/security-scanning.md` — the eight scanners, the thresholds, and why the findings document is the only way past one
- [ ] T035 [P] Add to `docs/anti-patterns.md`: CodeQL alongside semgrep, SBOM and signing with no consumer, a version-inferring release tool, Flux image automation duplicating Renovate, a nightly scheduled scan
- [ ] T036 [P] Add to `docs/gotchas.md`: the `workflow` token scope on HTTPS pushes (research E3), `fileMatch` → `managerFilePatterns`, `set -e` hiding seven of eight scanners, `pull_request_target` with a fork's code
- [ ] T037 Update `docs/walkthrough.md` with the real output of `make scan`, `scripts/check-ci-contract.sh` and one Renovate proposal
- [ ] T038 Run the `code-reviewer` agent over the diff against `.claude/rules/` and this spec; act on what it finds
- [ ] T039 Run `make test`, `make test-hooks`, `make scan` and `scripts/check-ci-contract.sh` one last time and show the output; then merge to `main`

## Dependencies

```
Phase 1 ──▶ Phase 2 ──▶ Phase 3 (US1) ──▶ Phase 4 (US2) ──▶ Phase 5 (US3) ──▶ Phase 6
             T005..T008     T009..T017        T018..T026        T027..T030
```

- T001 blocks T015 — the contract check must exist before the workflow it checks.
- T005 blocks T014 — the `scan` job calls `make scan`; there is nothing to call until it exists.
- T007 blocks T008 — the document must hold real findings before it can be made load-bearing.
- T020 blocks T023, and T023 blocks T026 — Renovate can only propose a bump once a newer tag exists.
- T025 is the user's, and everything after it in Phase 4 waits on it.

## Parallel opportunities

- Phase 1: T002, T003, T004 together (different files).
- Phase 3: T010, T011, T012, T013 together — four independent jobs in one workflow file, written as
  separate blocks and merged in one edit.
- Phase 6: T031–T036 together (six documents, no shared lines).

## Implementation strategy

**MVP is User Story 1 alone.** A repository where every change is checked, with no automated
updates and no publishing, is already worth having and is independently testable. US2 adds the
mechanism that keeps the pins from rotting; US3 adds the discipline that stops findings from
accumulating. Each phase ends somewhere the repository could honestly be left.
