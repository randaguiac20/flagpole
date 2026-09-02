<!--
Sync Impact Report
- Version change: (template) → 1.0.0
- Modified principles: none (initial ratification)
- Added sections: Core Principles (I–V), Technology and Delivery Constraints, Development Workflow, Governance
- Removed sections: none
- Templates reviewed: .specify/templates/plan-template.md (Constitution Check gate reads this file at runtime),
  spec-template.md, tasks-template.md — no edits required
- Follow-up TODOs: none
-->

# Flagpole Constitution

## Core Principles

### I. Spec Is the Source of Truth
User-visible behavior MUST be specified before it is built (`/speckit-specify` → `/speckit-clarify` →
`/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`). Code, tests, manifests
and decision records MUST cite the spec ID they serve (`001-flagpole-api` … `006-ci-and-security`).
When implementation reveals the spec is wrong, the spec changes first, then the code.
Rationale: the demo teaches SDD; a spec that trails the code teaches the opposite.

### II. Simplicity and Restraint
Flagpole has three concepts only: flags, environments, evaluation. No feature and no tooling
component (rule, skill, hook, agent, MCP server, plugin) is added without a concrete trigger recorded
in `docs/decisions/<component>.md`, including the cheaper alternative that was rejected. What was
deliberately NOT built MUST be documented (`docs/anti-patterns.md`). Complexity budget goes to clarity.

### III. Test-First and Deterministic (NON-NEGOTIABLE)
Every functional requirement has an automated test that fails before the implementation exists.
Evaluation and end-to-end tests are deterministic: no randomness, no timing-based assertions, no
network in unit tests. The fast test subset runs on every Stop hook; the full suite runs in CI.
Rationale: flaky demos teach nothing; determinism is what makes `sha256(key:user) % 100` the rule.

### IV. Security Baseline
No plaintext secret is ever committed; every `kind: Secret` is SOPS-encrypted with age. Least
privilege everywhere: `viewer`/`operator` roles enforced by a single dependency, PodSecurity
`restricted`, NetworkPolicy default-deny, non-root images pinned by digest. Every dependency is
maintained, pinned and scanned. A High or Critical finding stays open only with a written
accepted-risk entry in `docs/security-findings.md`.

### V. GitOps and Reproducibility
The cluster is changed only through git and Flux; `kubectl apply` into application namespaces is a
defect. The whole system MUST rebuild from an empty folder with the documented commands
(`docs/BLUEPRINT.md`, `make bootstrap && make cluster-up && make deploy && make e2e`). Ports are
checked before binding. Every claim of "it works" is verified by running the command and showing
its output.

## Technology and Delivery Constraints

Python 3.12 + FastAPI + uv (api, consumer, MCP server); React + TypeScript + Vite (web); k3d local
cluster; Flux for GitOps; SOPS + age for secrets; Renovate for dependency and image updates; Dex for
OIDC; GitHub Actions publishing to `ghcr.io/randaguiac20`. The cluster is local only. Sources are
official documentation, official images and charts, and upstream-maintained packages; no blog
snippets, no unmaintained packages (`docs/dependencies.md` lists each with a justification).

## Development Workflow

One feature branch per spec, named by Spec Kit (`NNN-name`). Conventional commits carry the spec ID
in the body. `/speckit-analyze` MUST pass before `/speckit-implement`. The `code-reviewer` agent
reviews every feature diff against `.claude/rules/` and the spec before merge. Chores (hooks, CI,
formatter config, documentation) do not get a spec but do get a decision record when they add a
Claude Code component.

## Governance

This constitution supersedes all other practices in the repository. Amendments are a pull request
that edits this file, bumps the version semantically (MAJOR: principle removed or redefined; MINOR:
principle or section added or materially expanded; PATCH: clarification), and records the change in
the Sync Impact Report comment at the top. Every `/speckit-plan` Constitution Check gate MUST pass
or document a justified exception in the plan's Complexity Tracking table. `CLAUDE.md` holds
operational facts (commands, layout, names) and MUST NOT restate these principles; it links here.

**Version**: 1.0.0 | **Ratified**: 2026-09-02 | **Last Amended**: 2026-09-02
