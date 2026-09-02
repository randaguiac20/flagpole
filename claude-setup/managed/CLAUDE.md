# Organization policy (managed CLAUDE.md example)

<!-- Installed by claude-setup/install-managed.sh to /etc/claude-code/CLAUDE.md (Linux/WSL),
     /Library/Application Support/ClaudeCode/CLAUDE.md (macOS) or C:\Program Files\ClaudeCode\CLAUDE.md (Windows).
     A managed CLAUDE.md is GUIDANCE that users cannot exclude with claudeMdExcludes. Anything that must be ENFORCED
     (deny rules, hooks, allowed marketplaces) belongs in managed-settings.json instead, not here. -->

- Never paste customer data, credentials, or private keys into a prompt. Redact before sharing logs.
- Prefer the organization's internal package mirror; report any dependency that is not on it.
- Every repository change goes through a pull request. Direct pushes to `main` are not allowed.
- When unsure whether an action is destructive, stop and ask the human.
