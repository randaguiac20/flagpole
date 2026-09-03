# Quickstart: ci-and-security

How to prove this feature works. Every step is a command and an expected output; a step that is only
read, not run, proves nothing.

## Prerequisites

```bash
gh auth status                  # logged in to github.com as randaguiac20
gh api repos/randaguiac20/flagpole --jq .default_branch   # main
for t in trivy hadolint osv-scanner gitleaks semgrep bandit pip-audit actionlint; do
  command -v "$t" >/dev/null && echo "ok   $t" || echo "MISSING $t"
done
```

`actionlint` is the one tool this feature adds. `renovate-config-validator` comes from
`npx --yes --package renovate -- renovate-config-validator`; no global install.

## 1. The local scan is the same scan (FR-013, SC-007)

```bash
make scan
```

Expect: eight sections, then a summary table. The run does **not** stop at the first finding —
that is the point of `scan.sh` over eight separate commands. Exit status is 0 only when nothing
reaches its failing threshold, or when everything that does is already recorded in
`docs/security-findings.md`.

Prove the threshold bites, then undo it:

```bash
printf 'password = "hunter2"  # gitleaks:probe\n' >> /tmp/probe.py
cp /tmp/probe.py backend/app/_probe.py && make scan ; rm backend/app/_probe.py
```

Expect a gitleaks finding and a non-zero exit. If it passes, the check is decorative.

## 2. The contract holds (FR-001..FR-005, FR-007)

```bash
scripts/check-ci-contract.sh
```

Expect a line per assertion and `N passed, 0 failed`. Prove it can fail:

```bash
sed -i 's/pull_request:/pull_request_target:/' .github/workflows/ci.yml
scripts/check-ci-contract.sh ; git checkout .github/workflows/ci.yml
```

Expect a failure naming FR-007. (Copy the file aside before mutating it if it is not yet
committed — gotcha #25.)

```bash
actionlint .github/workflows/*.yml
npx --yes --package renovate -- renovate-config-validator renovate.json
```

Expect no output from `actionlint` and `Config validated successfully` from the validator.

## 3. A change is checked before anyone looks at it (US1, SC-001)

Push the branch and open a change:

```bash
git push -u origin 006-ci-and-security
gh pr create --fill
gh pr checks --watch
```

Expect every job green. Then prove SC-001 — a broken test must be visible on the change:

```bash
sed -i 's/assert response.status_code == 200/assert response.status_code == 418/' \
  backend/tests/test_health.py
git commit -am "test: deliberately break a test to prove the gate" && git push
gh pr checks --watch          # test-backend must fail
git revert --no-edit HEAD && git push
```

## 4. A documentation change runs no build (FR-004, SC-003)

```bash
echo >> docs/gotchas.md && git commit -am "docs: whitespace" && git push
gh run list --branch 006-ci-and-security --limit 3
```

Expect a `ci` run and **no** `release` run.

## 5. Publishing (FR-005, SC-004)

After merging to `main`:

```bash
gh run list --workflow release.yml --limit 1
gh api /users/randaguiac20/packages/container/flagpole-api/versions \
  --jq '.[0].metadata.container.tags'
```

Expect both tags — the contents of `VERSION` and `sha-<short commit>`. Then trace an image back to
its source, which is SC-004:

```bash
docker buildx imagetools inspect ghcr.io/randaguiac20/flagpole-api:$(cat VERSION) \
  --format '{{ json .Provenance }}' 2>/dev/null || \
  docker image inspect ghcr.io/randaguiac20/flagpole-api:$(cat VERSION) \
    --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}'
```

Expect the commit SHA the workflow ran against.

Prove the republish guard: run `release.yml` again without changing `VERSION`.

```bash
gh workflow run release.yml --ref main && gh run watch
```

Expect a failure naming `VERSION`, not a silently moved tag.

## 6. Dependencies are proposed, not chased (US2, SC-005)

**This step needs the user.** Installing a GitHub App is an account action:

> https://github.com/apps/renovate → Configure → randaguiac20 → select `flagpole`

Then:

```bash
gh pr list --author app/renovate
```

Expect the "Dependency Dashboard" issue and at least one grouped update. Take one through to the
cluster, which is what SC-005 actually asserts:

```bash
gh pr checks <n> && gh pr merge <n> --squash
flux reconcile kustomization flagpole-dev --with-source
scripts/verify-cluster.sh
```

Expect the cluster to follow with no manual step, and the verification to still pass.

## 7. Findings are triaged (US3, SC-006)

```bash
grep -c '^| 20' docs/security-findings.md      # one row per finding
make scan                                       # exit 0
```

Expect every finding the scanners currently report at or above its threshold to have a row with a
decision, a reason and a date — and `make scan` to pass *because* of those rows, not because the
scanners found nothing.

## 8. No credential in any log (FR-014, SC-008)

```bash
gh run view --log $(gh run list --limit 1 --json databaseId --jq '.[0].databaseId') \
  > /tmp/run.log
gitleaks detect --no-git --source /tmp/run.log
grep -nE 'ghp_|gho_|github_pat_|BEGIN [A-Z ]*PRIVATE KEY|age1[a-z0-9]{50,}' /tmp/run.log
rm /tmp/run.log
```

Expect no leaks and no matches. GitHub masks registered secrets, but masking is not the guarantee —
not printing them is.
