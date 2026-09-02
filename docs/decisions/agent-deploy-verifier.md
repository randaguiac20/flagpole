# Decision: subagent `deploy-verifier`

- **Problem / trigger**: after `/deploy-local`, proving readiness means ~10 kubectl/flux commands and reading events; the skill should end with a verdict, not a log. Serves `005-platform-delivery` (SC: all Ready, secrets decrypted, `/readyz` from inside the cluster).
- **Alternative rejected**: `cluster-status-mcp` (cut: kubectl/flux are CLIs; an MCP server would wrap them for no gain, see `cluster-status-mcp.md`); inline steps in the skill (floods context).
- **Limits**: read-only kubectl/flux verbs + `kubectl run` for the in-cluster curl; never reads secret values; `maxTurns: 30`.
- **Not done**: no write access, no `helm` (Flux owns releases). Signal: a verification that needs a mutation → it is not a verification.
- **Verification**: `/agents`; walkthrough in Phase 4 with PASS/FAIL table. Pending.
