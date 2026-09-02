# Decision: `cluster-status-mcp` — NOT built

- **Problem it would solve**: give Claude rollout and Flux readiness data. But `kubectl` and `flux` are CLIs that already work from Bash, and their output is small and structured (`-o json`, `--no-header`).
- **Decision test**: rule 5 ("If a CLI already exists, prefer Bash + a skill over a new MCP server") fails it outright. The "learn to build one" motive is already served by `flagpole-mcp`.
- **What replaces it**: the `deploy-verifier` agent with read-only `kubectl get/describe/logs` and `flux get/events` in its `tools`, plus the session-start hook for a one-line readiness summary.
- **Signal that would justify building it**: a cluster Claude cannot reach from the shell (remote, no kubeconfig on this machine) or a need for typed, permission-scoped read-only tools handed to a third party.
- **Recorded as** an anti-pattern example in `docs/anti-patterns.md` (MCP wrapping a CLI). Confirmed with the user on 2026-09-02.
