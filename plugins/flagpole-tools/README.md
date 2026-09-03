# flagpole-tools

The three procedures for running [Flagpole](https://github.com/randaguiac20/flagpole) locally, and
the two agents they delegate to.

| Component | Kind | What it does |
|---|---|---|
| `/flagpole-tools:deploy-local` | skill, user-invoked only | build the images, import them into k3d, reconcile Flux, then hand verification to `deploy-verifier` |
| `/flagpole-tools:security-scan` | skill, user-invoked only | `make scan`, then triage through `security-auditor` into a fixed table |
| `/flagpole-tools:e2e` | skill | the Playwright suite, headless, summarised by scenario |
| `flagpole-tools:deploy-verifier` | agent, read-only | asserts a deployed cluster against its contract |
| `flagpole-tools:security-auditor` | agent, read-only | runs the scanners and returns a triaged report |

## Install

From a clone of the Flagpole repository:

```bash
claude plugin marketplace add ./     # the leading ./ is required; a bare . is rejected
claude plugin install flagpole-tools@flagpole-local
```

Inside the repository nothing needs installing: `.claude/settings.json` declares both the marketplace
and the plugin, so trusting the folder is enough.

## What is deliberately not here

Every hook. A plugin can be disabled with one command, and a guard that can be switched off is not a
guard — the GitOps and secret guards stay in the repository's own `.claude/settings.json`. See
`docs/decisions/plugin-flagpole-tools.md`.
