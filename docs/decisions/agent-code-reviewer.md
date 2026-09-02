# Decision: subagent `code-reviewer`

- **Problem / trigger**: reviewing a feature diff against 4 rule files and a spec reads many files and produces long output the main session will not reference again; and the reviewer must not edit. Serves every spec (review gate before merge).
- **Alternative rejected**: `/code-review` bundled skill (does not know our spec IDs/rules format); asking the main session to review (floods context, and it just wrote the code).
- **Limits**: `tools: Read, Grep, Glob, Bash(git diff *), Bash(git log *), Bash(git status *)` (read-only), `maxTurns: 25`, one-paragraph system prompt, max 15 findings.
- **Not done**: no `memory:` (a reviewer that "remembers" past verdicts drifts from the spec); no `isolation: worktree`. Signal: the same false positive raised in three reviews → project memory.
- **Verification**: `/agents` lists it; walkthrough: run on branch `001-flagpole-api`, paste the verdict table. Pending: Phase 3.
