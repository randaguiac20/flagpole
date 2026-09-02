# Decision: hook `InstructionsLoaded` → `instructions-loaded.sh` (documented, disabled)

- **Problem / trigger**: proving *when* CLAUDE.md, rules and path-scoped rules load is the memory lesson; nothing else in the repo needs it.
- **Alternative rejected**: `/context` alone (shows what is loaded now, not when/why); enabling it in the shared settings (observability for one person, cost for all).
- **Limits**: shipped only in `.claude/settings.local.json.example`; appends one line per load to `.claude/logs/instructions-loaded.log`; no stdout; event has no decision control anyway.
- **Not done**: not enabled by default. Signal: a rule that "did not load" complaint → enable locally, read the log, disable again.
- **Verification**: `make test-hooks` ("appends a log line"); walkthrough step: enable, start a session, read a `.py` file, expect a `path_glob_match` line for `python-services.md`. Pending: user-run.
