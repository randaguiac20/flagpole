# Data Model: ci-and-security

No database and no schema. The entities in the spec are files and run outputs; this records their
shape so the contract check has something to assert against.

## Version

**File**: `VERSION` (repository root)

**Shape**: exactly one line, `MAJOR.MINOR.PATCH`, no leading `v`, terminated by a newline.

| Rule | Where enforced |
|---|---|
| Matches `^[0-9]+\.[0-9]+\.[0-9]+$` | `scripts/check-ci-contract.sh`; `release.yml` before it builds |
| Changed by a person (FR-005a) | Nothing writes it — no job, script or bot has it as an output |
| Must not already exist in the registry | `release.yml` queries the registry and fails, naming the file to bump |

**Consumers**: `release.yml` (image tags), `scripts/build.sh` via `FLAGPOLE_IMAGE_TAG`, and Renovate
indirectly — it reads the *tags in `deploy/`*, which a newer published version makes stale.

## Published image

One per service, three per publish.

| Field | Value |
|---|---|
| Repository | `ghcr.io/randaguiac20/flagpole-{api,consumer,web}` |
| Version tag | the contents of `VERSION` |
| Commit tag | `sha-<first 7 of the commit>` |
| Labels | `org.opencontainers.image.{revision,source,version,created}` from `docker/metadata-action` |

Both tags point at the same digest. FR-005 is satisfied by the pair: the version is what a person
reads in `deploy/`, the commit tag is what makes SC-004 answerable.

## Finding

**File**: `docs/security-findings.md` — a table, newest first.

| Column | Meaning | Allowed values |
|---|---|---|
| Date | when the decision was made | `YYYY-MM-DD` |
| Scanner | which tool reported it | one of the eight |
| Identifier | what it reported | CVE / GHSA / rule id / `DL####` |
| Severity | as the scanner rated it | `CRITICAL`, `HIGH`, `MEDIUM`, `LOW` |
| Where | file, package or image | free text |
| Decision | what was done about it | `fixed`, `accepted`, `not applicable`, `deferred` |
| Reason | why that decision | one sentence, and for `deferred` a condition that ends it |

**Rule**: a finding at or above the failing threshold (research E6) fails the run until it appears
here. `accepted` and `not applicable` need a reason that names why the code is not reachable or why
the risk is tolerable; "low priority" is not a reason.

**State**: a row is never deleted. A `fixed` row stays as the record that it was once true.

## Check run

Not a file — the shape the contract asserts on the workflows.

| Property | `ci.yml` | `release.yml` |
|---|---|---|
| Triggers | `pull_request`, `push: [main]` | `push: [main]` with `paths-ignore` |
| `permissions` | `contents: read` | `contents: read`; `packages: write` on the publish job only |
| `concurrency` | group per workflow+ref, cancel in progress | same |
| Jobs | `lint`, `test-backend`, `test-consumer`, `test-mcp`, `test-frontend`, `test-hooks`, `scan` | `publish` |
| Secrets referenced | none | `GITHUB_TOKEN` only, in `publish` |
| Forbidden | `pull_request_target` anywhere; `secrets.` outside `publish` | same |

## Update proposal

Produced by Renovate, not by this repository. Recorded here because the contract asserts the
configuration that shapes it.

| Property | Value |
|---|---|
| Managers enabled | `pep621`, `npm`, `dockerfile`, `github-actions`, `pre-commit`, `helm-values`, `flux`, `kubernetes` |
| Digest pinning | `pinDigests: true` — an update must not turn a digest back into a tag |
| Grouping | non-major grouped per ecosystem; major ungrouped |
| Schedule | `before 6am on monday` |
| Concurrency | `prConcurrentLimit: 3` |
| Automerge | `false` everywhere (FR-009) |
