# Decision: project CLAUDE.md

- **Problem / trigger**: every session needs the same facts: commands, layout, names, the four "must hold" conventions. Without them Claude re-derives (and gets wrong) ports, namespaces and the Flux-owns-the-cluster rule. No spec ID (chore).
- **Alternative rejected**: putting architecture, API conventions and deploy procedures in it too. Those are reference/procedural and moved to `docs/architecture.md` (imported), the `api-conventions` skill and `/deploy-local`.
- **Limits**: 57 lines (< 150 budget; docs recommend < 200). One `@` import. Links to the constitution and `specs/`, never restates them. No "every time X do Y" (that is a hook).
- **Not done, and the signal to do it**: no nested `CLAUDE.md` per service. Add one under `frontend/` only if a frontend-only convention is violated twice and does not fit a path-scoped rule.
- **Verification**: `/context` in a fresh session lists `CLAUDE.md` and `docs/architecture.md` under Memory; `/memory` shows the same. Pending: user-run, output goes in `docs/walkthrough.md`.
