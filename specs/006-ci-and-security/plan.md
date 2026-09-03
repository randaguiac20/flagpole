# Implementation Plan: ci-and-security

**Branch**: `006-ci-and-security` | **Date**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-ci-and-security/spec.md`

## Summary

Two GitHub Actions workflows and one Renovate configuration. `ci.yml` runs on every change: lint,
each service's tests, the hook tests, and the scanners — the same set `make scan` runs locally, so a
finding cannot depend on where it was found. `release.yml` runs only on the default branch and
publishes three images tagged with the `VERSION` file and with the commit.

Renovate arrives as the Mend-hosted app, which the user installs on the repository once; nothing here
holds a token for it. Its configuration covers every kind of pin feature 005 introduced — Python and
npm packages, image digests, chart versions, pre-commit hooks and the Actions themselves — grouped so
the number of changes to review stays small.

`scripts/scan.sh` is written first, because `make scan` is the local half of FR-013 and the workflow
should call it rather than restate it.

## Technical Context

**Language/Version**: no new language. Bash for `scan.sh`; YAML for the workflows; JSON for Renovate

**Primary Dependencies**: GitHub Actions; the scanners already named in the Makefile — `pip-audit`,
`npm audit`, `osv-scanner`, `trivy`, `hadolint`, `gitleaks`, `bandit`, `semgrep`; Renovate via the
Mend app

**Storage**: none. `docs/security-findings.md` is the only durable output

**Testing**: `scripts/check-ci-contract.sh` asserts the workflows against
`contracts/ci-contract.json`; `actionlint` for the workflow syntax; `renovate-config-validator` for
the configuration; and the workflows are proved by a change that deliberately fails

**Target Platform**: GitHub-hosted runners, `ubuntu-latest`

**Project Type**: delivery and verification — no new service

**Performance Goals**: a typical change's checks finish in a few minutes; a documentation-only change
runs no build at all

**Constraints**: nothing writes to the cluster (Flux owns it); credentials reach only the steps that
need them and never a fork's change; every tool version pinned so the same commit gives the same
answer; no credential in any log

**Scale/Scope**: two workflows, one Renovate configuration, one scanner script, one findings document

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Verdict |
|---|---|---|
| I. Spec is the source of truth | Behaviour traces to FRs; the versioning question was settled before the plan | **PASS** — the clarification is in the spec, and FR-005a says a person changes the version |
| II. Simplicity and restraint | Fewest moving parts that satisfy the spec | **PASS** — two workflows, not a matrix of six; the scanners already chosen rather than new ones; no release tool; no self-hosted updater |
| III. Test-first and deterministic | Every behaviour has a check that fails first; no randomness | **PASS** — the contract check is written before the workflows, every tool version is pinned, and the workflows are proved by a change that deliberately fails rather than by reading them |
| IV. Security baseline | Least privilege; no secret in output | **PASS** — read-only permissions by default, write only on the publishing job, nothing privileged for a fork, and FR-014 asserted by a check |
| V. GitOps and reproducibility | Configuration, not code; rebuild from empty | **PASS** — publishing is where continuous integration stops; the cluster changes only when a manifest is merged, which is feature 005's mechanism |

**Re-check after Phase 1 design**: unchanged. One judgement call is worth naming: the workflows call
`make` targets rather than restating their steps. That costs a little clarity in the workflow file and
buys the guarantee FR-013 asks for — that the local run and the automated run cannot drift, because
they are the same command.

## Project Structure

### Documentation (this feature)

```text
specs/006-ci-and-security/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── ci-contract.json # jobs, triggers, permissions and the scanner set
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
.github/
├── workflows/
│   ├── ci.yml           # every change: lint, tests, hook tests, scanners
│   └── release.yml      # default branch only: build and publish three images
└── dependabot.yml       # NOT used — see research F5 for why Renovate instead

renovate.json            # every kind of pin this repository uses, grouped
VERSION                  # the one place the image version is decided (FR-005a)
scripts/
├── scan.sh              # the scanner set, run identically here and in CI
└── check-ci-contract.sh # asserts the workflows against the contract
docs/
├── security-findings.md # every finding: severity, decision, reason, date
└── renovate.md          # what is updated, how it is grouped, what is pinned by hand
```

## Complexity Tracking

| Addition | Why it is not avoidable | What was rejected |
|---|---|---|
| A second workflow for publishing | FR-004 and FR-005: a documentation change must not build, and only the default branch may publish. One workflow with conditions on every job hides that rule inside expressions | One workflow with `if:` on each job (the rule becomes six conditions nobody can read together); publishing from the same job as the tests (a fork's change would need the registry credential) |
| A findings document | FR-012. A scanner's output is a terminal scrollback; a decision needs somewhere to live | Suppression files per scanner (the reason lives next to the rule, not next to the risk, and nobody reads eight of them); an issue tracker (a second place, for a repository whose lesson is that the answer is in the repository) |
| A `VERSION` file | The user's decision, and FR-005a. The updater needs a newer tag to notice | Deriving it from commit wording (a release tool, a changelog and a tagging step, and the version becomes a side effect); commit-sha tags only (no readable version in the manifests) |
| `scripts/scan.sh` rather than steps in the workflow | FR-013 requires the local and automated runs to agree. Two lists of scanners is how they stop agreeing | Listing the scanners in the workflow (drift); a container image holding them (a build to maintain for a demo) |
