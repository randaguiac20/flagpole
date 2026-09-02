# Decision: skill `/deploy-local`

- **Problem / trigger**: build → import → reconcile source → reconcile kustomization → wait → verify is a 5-step procedure that would be pasted into chat every deploy. Serves `005-platform-delivery`.
- **Alternative rejected**: `make deploy` alone (no delegation to `deploy-verifier`, no explanation of why `kubectl apply` is wrong); a CLAUDE.md paragraph (procedural content, wrong place).
- **Limits**: `disable-model-invocation: true` (side effects on the cluster; only the user triggers it), `allowed-tools` limited to make/scripts/k3d/flux/kubectl get, dynamic preflight via `` !`k3d cluster list` ``.
- **Not done**: no `context: fork` (the user wants to watch the deploy step by step). Signal: deploy output routinely > 200 lines.
- **Verification**: `/deploy-local` appears in the `/` menu; Phase 4 walkthrough. Pending.
