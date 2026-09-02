# Decision: skill `/add-flag-field`

- **Problem / trigger**: a flag field crosses spec, model, migration, API, audit log, MCP, UI, seed and tests: ten places, easy to miss one. Model-invocable so Claude picks it up when a task mentions a new flag attribute. Serves `001`, `002`, `004`.
- **Alternative rejected**: CLAUDE.md checklist (30 lines of procedure in an always-on file); a subagent (the work is sequential edits the user wants to see).
- **Limits**: model-invocable, no side effects, `$0`/`$1` arguments.
- **Not done**: no code generation templates. Signal: the checklist followed correctly three times with identical boilerplate → add a generator script.
- **Verification**: Phase 3 walkthrough (used once when the spec adds a field). Pending.
