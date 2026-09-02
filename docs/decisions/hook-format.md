# Decision: hook `PostToolUse(Edit|Write)` → `format.sh`

- **Problem / trigger**: formatting drift in Python and TypeScript shows up as CI failures and noisy diffs. "Run ruff after editing" in CLAUDE.md was not sufficient because it is forgotten under load, and it needs no reasoning.
- **Alternative rejected**: pre-commit only (later, and produces a second commit); a `Stop` hook running the formatter over the tree (mutates untouched files, forbidden by §2.4).
- **Limits**: one handler, no `if` (six `if` variants for py/ts/tsx × Edit/Write were noise; the script switches on the extension in ~10 ms), `timeout: 10`, formats **only the touched file**, no stdout, fail-open when the formatter is missing (logged).
- **Not done**: no `ruff check --fix` (a linter can change semantics; it runs in CI and pre-commit), no import sorting. Signal: lint failures that are always auto-fixable.
- **Verification**: `make test-hooks` ("ruff rewrote the file"); live on 2026-09-02: the harness reported "PostToolUse hook modified … (likely a formatter)" after an Edit and a Write; `.claude/logs/hooks.log` shows `format ruff format …`.
