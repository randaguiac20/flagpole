# Feature Specification: ci-and-security

**Feature Branch**: `006-ci-and-security`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "006-ci-and-security: make the checks that protect this repository run without anybody remembering to run them. Continuous integration on every change: lint, tests, the scanners, and images built and published with a version tag. Dependency updates proposed automatically, including the container digests and the chart versions feature 005 pinned. Findings triaged and written down rather than left in a terminal. Non-goals: no deployment from CI (Flux owns the cluster), no new scanners for their own sake, no security theatre."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Every change is checked before anyone looks at it (Priority: P1)

Someone opens a change. Without asking, the same checks that run locally run again on a clean
machine, and the result is visible on the change itself. A change that breaks a test, fails a lint,
or introduces a known vulnerability says so before a person reads a line of it.

**Why this priority**: A check that only runs when someone remembers is not a check. Everything else
in this feature depends on there being a place where the answer is authoritative.

**Independent Test**: Open a change that breaks a test and see the result reported against it; fix
the test and see the result change.

**Acceptance Scenarios**:

1. **Given** a change to any service, **When** it is pushed, **Then** that service's lint and tests
   run and the outcome is reported against the change.
2. **Given** a change that breaks a test, **When** the checks run, **Then** they fail and name the
   test.
3. **Given** a change that touches only documentation, **When** the checks run, **Then** they do not
   spend time building images.
4. **Given** the checks pass, **When** the change reaches the default branch, **Then** images are
   published with a version tag.
5. **Given** the same commit checked twice, **When** the results are compared, **Then** they agree —
   nothing in the checks depends on the day or the machine.

---

### User Story 2 - Dependencies are proposed, not chased (Priority: P1)

Updates arrive as changes to review rather than as a task someone has to remember. That includes the
things feature 005 pinned: the container digests, the chart versions, and the tool versions.

**Why this priority**: Pinning without a mechanism to update is how a repository becomes a museum of
old vulnerabilities. Equal to US1 because the pins were only defensible on the promise of this.

**Independent Test**: Confirm a proposal appears for something out of date, and that merging it
changes exactly the pin and nothing else.

**Acceptance Scenarios**:

1. **Given** a dependency with a newer version, **When** the updater runs, **Then** it proposes a
   change that updates that pin.
2. **Given** a proposal, **When** it is opened, **Then** the same checks as any other change run
   against it.
3. **Given** an image digest pinned in a Dockerfile or a manifest, **When** the image is rebuilt
   upstream, **Then** the digest is proposed for update like any other dependency.
4. **Given** many updates at once, **When** they are proposed, **Then** they arrive in a reviewable
   number of changes rather than one per package per day.

---

### User Story 3 - Findings are triaged, not accumulated (Priority: P2)

Every scanner finding is either fixed, or written down with a reason and a date. Nothing sits
unexplained, and nobody has to re-derive last month's judgement.

**Why this priority**: Scanners produce findings faster than anyone fixes them, and an unread list is
indistinguishable from a clean one. P2 because the checks must exist before there is anything to
triage.

**Independent Test**: Read the findings document and confirm every current finding appears with a
decision and a date.

**Acceptance Scenarios**:

1. **Given** the scanners run, **When** they report a finding, **Then** it is fixed or recorded with
   why it was not, and when that judgement was made.
2. **Given** a recorded finding, **When** the underlying issue is fixed, **Then** the record says so
   rather than being deleted.
3. **Given** a finding that cannot be fixed here, **When** it is recorded, **Then** the record names
   what would have to change.

---

### Edge Cases

- **A scanner's own database is unavailable**: the check fails loudly rather than passing with no
  findings — a scanner that cannot scan must never look clean.
- **A dependency has no newer version**: no proposal, and no empty change.
- **An update proposal fails the checks**: it stays open with the failure visible; nothing merges
  itself.
- **A finding has no fix available upstream**: it is recorded with that fact and the date, not
  silently ignored.
- **The registry rejects a push**: the change is reported as failed. Every cause that can be
  detected before building is checked first, for all three services at once, so the common case
  leaves nothing behind. A registry offers no transaction, so a failure part-way through the third
  push can still leave two services published at the new version; that is a real limit, stated here
  rather than claimed away, and the recovery is to fix the cause and re-run — the version is
  unchanged, so the two already-published tags are the same images.
- **A fork or an outside change**: checks run, but nothing that could publish or write runs with
  credentials.

## Clarifications

### Session 2026-09-02

- Q: How is the image version decided, so the updater has a newer tag to propose? → A: A single
  `VERSION` file, bumped by hand in the change that earns it. Publishing from the default branch
  tags images with that version and with the commit. The updater then sees the newer tag and
  proposes the bump in the deployment manifests. Deriving the version from commit wording was
  rejected: it adds a release tool, a changelog and a tagging step, and makes the version a side
  effect of how a message was phrased rather than a decision someone made.

- Q: What does "fast enough" mean for SC-002, so it can be measured rather than argued? → A: 10
  minutes end to end for a typical change. Set during `/speckit-analyze`, which flagged the original
  wording as unmeasurable. The figure is a budget, not a measurement: if the checks exceed it, the
  answer is to split or cache a job, not to raise the number quietly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every change MUST run, on a clean machine: the lint and tests of each service it
  touches, the hook tests, and the scanners.
- **FR-002**: The result MUST be visible against the change itself, naming what failed.
- **FR-003**: Checks MUST be reproducible: the same commit MUST produce the same result, so every
  tool version is pinned and nothing resolves "latest" at run time.
- **FR-004**: A change that touches only documentation MUST NOT build or publish images.
- **FR-005**: Images MUST be published only from the default branch, tagged with the version held in
  a single file in this repository and with the commit they were built from.
- **FR-005a**: That version MUST be changed by a person, in the change that earns it. Nothing may
  infer it from commit messages or increment it automatically.
- **FR-006**: Nothing in the checks may write to the cluster. Flux owns the cluster; publishing an
  image is where continuous integration stops.
- **FR-007**: Credentials MUST be available only to the steps that need them, and never to a change
  from a fork.
- **FR-008**: Dependency updates MUST be proposed automatically for every kind of pin this
  repository uses: language packages, container images by digest, chart versions, tool versions and
  the hooks themselves.
- **FR-009**: Update proposals MUST be grouped so that the number of changes to review stays small,
  and MUST NOT merge themselves.
- **FR-010**: The scanners MUST cover: language dependencies, container images, infrastructure
  definitions, source code, and secrets.
- **FR-011**: A scanner that cannot run MUST fail the check rather than report nothing.
- **FR-012**: Every finding MUST be fixed or recorded with a decision, a reason and a date.
- **FR-013**: The same scanner set MUST be runnable locally with one command, producing the same
  findings as the automated run.
- **FR-014**: No credential, token or key may appear in any log the checks produce.

### Key Entities

- **Check run**: everything that happens for one change — its steps, their outcomes, and the commit
  they ran against.
- **Published image**: one per service, tagged with a version and traceable to a commit.
- **Update proposal**: a change that alters one or more pins and nothing else.
- **Finding**: something a scanner reported, with a severity, a decision, a reason and a date.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A change that breaks a test cannot reach the default branch without the failure being
  visible on it.
- **SC-002**: The checks for a typical change finish within 10 minutes end to end, so that waiting
  for them is cheaper than merging around them.
- **SC-003**: A documentation-only change runs no build.
- **SC-004**: Every image on the default branch can be traced to the commit it was built from.
- **SC-005**: At least one dependency update is proposed, reviewed and merged, and the cluster
  follows it without a manual step.
- **SC-006**: Every finding the scanners currently report appears in the findings document with a
  decision and a date.
- **SC-007**: `make scan` locally and the automated run report the same findings for the same commit.
- **SC-008**: No log produced by the checks contains a credential.

## Assumptions

- The automation runs on GitHub Actions and publishes to GitHub's container registry, because the
  repository is already there and adding a second service would be a decision without a reason.
- Dependency proposals come from the Mend-hosted Renovate app, installed on the repository by the
  user once. Nothing in this repository holds a token for it.
- Publishing is where this feature ends. The cluster is reconciled by Flux from the repository, so a
  new image reaches the cluster when a change to a manifest is merged — which is feature 005's
  mechanism, not a new one.
- The scanners are the ones already named in the Makefile. This feature makes them run and makes
  their findings answerable; it does not add scanners to look thorough.
- "Security" here means the checks a small team can actually keep up with. Where a real deployment
  would need more — signed images, provenance, a vulnerability service level — the decision records
  say so rather than pretending the demo has it.
