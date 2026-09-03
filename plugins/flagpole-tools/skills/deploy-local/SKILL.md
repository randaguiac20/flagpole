---
name: deploy-local
description: Build the Flagpole images, import them into the k3d cluster, reconcile Flux (source + flagpole-dev), wait for Ready, then hand verification to the deploy-verifier agent. Side effects on the cluster, so only the user invokes it.
disable-model-invocation: true
argument-hint: "[dev|prod] [--skip-build]"
allowed-tools: Bash(make *), Bash(scripts/*), Bash(k3d *), Bash(flux *), Bash(kubectl get *), Bash(git status *), Agent(flagpole-tools:deploy-verifier)
---

Deploy the current working tree to the local k3d cluster and prove it is serving. Target overlay: `$0` (default `dev`).

Current state (do not skip; if the cluster is missing, stop and tell the user to run `make cluster-up`):

!`k3d cluster list 2>/dev/null | tail -n +2 || echo "k3d not available"`
!`git status --porcelain | wc -l | xargs -I{} echo "{} uncommitted files"`

Steps, in order, showing the command and its last lines each time:
1. Unless `--skip-build` was given: `make build` (digest-pinned bases, non-root, HEALTHCHECK). Stop on failure.
2. `make deploy` — imports the images with `k3d image import`, then `flux reconcile source git flagpole` and `flux reconcile kustomization flagpole-$0 --with-source`, and waits for `Ready` on the Kustomization and every Deployment it owns.
3. Never `kubectl apply` anything. If a manifest is wrong, fix it under `deploy/`, commit, and re-run step 2. Flux only deploys what is in git: an uncommitted manifest change is not deployed.
4. Delegate verification: spawn the `flagpole-tools:deploy-verifier` agent with the overlay name and paste its PASS/FAIL table verbatim.
5. Finish with the URLs (`https://$0.flagpole.localhost`) and the Flux revision that is live (`flux get kustomization flagpole-$0`).
