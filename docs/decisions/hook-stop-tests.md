# Decision: hook `Stop` → `stop-tests.sh`

- **Problem / trigger**: "done" claims with red unit tests. CI catches them later; the point is a guardrail inside the session.
- **Alternative rejected**: a CLAUDE.md "run tests before finishing" line (skipped when the turn feels complete); a `type: prompt` Stop hook (calls the model; forbidden by §2.4).
- **Limits**: runs only when service code is uncommitted-changed (`git status` on `backend consumer mcp frontend/src .claude/hooks`); fingerprint stored in `.claude/state/` so the same state never blocks twice; honors `stop_hook_active`; `timeout: 120` on a `< 60 s` target (`make test-fast`); JSON `decision: block` with the last 20 lines. Fail-open on missing tooling.
- **Not done**: no frontend tests in the fast set (Vitest startup is too slow for a Stop gate; `make test` and CI run them). Signal: a UI regression that unit tests would have caught reaching CI twice.
- **Verification**: 5 cases in `make test-hooks` (short-circuit, clean tree, block once, no double block, pass). Live: this session's turns end with "Stop gate: running make test-fast" only when code changed.
