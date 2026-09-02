# Decision: subagent `security-auditor`

- **Problem / trigger**: `make scan` prints thousands of lines (trivy, semgrep). Only the triage belongs in the main conversation. Serves `006-ci-and-security`.
- **Alternative rejected**: `/security-review` bundled skill (code-only, does not run our scanners); the `security-scan` skill alone (would dump scanner output into the main context).
- **Limits**: read-only tools plus the scanner commands only; `maxTurns: 30`; reports against `docs/security-findings.md`; never fixes.
- **Not done**: not a `type: agent` hook on Stop (would call the model on every turn). Signal: a High finding merged twice without triage.
- **Verification**: `/agents` lists it; walkthrough in Phase 5 with real `make scan` output. Pending.
