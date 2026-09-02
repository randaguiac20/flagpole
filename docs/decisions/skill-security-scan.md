# Decision: skill `/security-scan`

- **Problem / trigger**: the triage template (severity/tool/location/decision/rationale/owner) must be identical every time so `docs/security-findings.md` stays consistent. Serves `006-ci-and-security`.
- **Alternative rejected**: `make scan` + free-form summary; the auditor agent alone (it returns findings, the skill owns the template and the fix/accept workflow).
- **Limits**: `disable-model-invocation: true`; `allowed-tools` = `make scan`, `scripts/scan.sh`, `Agent(security-auditor)`.
- **Not done**: no auto-fixing of findings. Signal: the same dependency bump applied by hand three times → Renovate already covers it.
- **Verification**: Phase 5 walkthrough. Pending.
