---
name: security-scan
description: Run every scanner (pip-audit, npm audit, osv-scanner, trivy image+config, hadolint, gitleaks, bandit, semgrep) via make scan, then triage with the security-auditor agent using the fixed template below. Slow and noisy, so only the user invokes it.
disable-model-invocation: true
argument-hint: "[tool-name]"
allowed-tools: Bash(make scan *), Bash(scripts/scan.sh *), Agent(flagpole-tools:security-auditor)
---

Run the full scanner set (or only `$0` if given) and produce the triage the maintainer records in `docs/security-findings.md`.

1. Spawn the `flagpole-tools:security-auditor` agent with: "Run `make scan$0` and triage every finding; compare with docs/security-findings.md." Wait for its report.
2. Present the report using exactly this template, one row per finding, High/Critical first:

   | Severity | Tool | Location | Finding | Decision (fix / accept / false-positive) | Rationale | Owner |

3. For each row marked **fix**, propose the smallest change (dependency bump, Dockerfile line, code change) and ask before applying anything that changes a pinned version.
4. For each row marked **accept** or **false-positive**, add the entry to `docs/security-findings.md` with the date and rationale so CI's baseline matches.
5. The gate is: **no open High/Critical**. Say explicitly whether the gate passes.
