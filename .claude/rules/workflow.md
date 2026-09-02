# Workflow rules (always loaded)

- **Spec first.** Features (user-visible behavior) go through Spec Kit: `/speckit-specify` → `/speckit-clarify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-implement`. Tooling chores (hooks, CI, formatter config, docs) do not get a spec. If the code needs to differ from the spec, change the spec first.
- **One feature branch per spec**, named by Spec Kit (`001-flagpole-api`, …). Chores commit on `main`.
- **Conventional commits**: `type(scope): summary` with `type` ∈ feat, fix, docs, chore, ci, test, refactor, build. Feature commits carry the spec ID in the body (`Spec: 001-flagpole-api`).
- **Never commit** `.env`, `CLAUDE.local.md`, `.claude/settings.local.json`, `.claude/logs/`, `*.agekey`, or a plaintext `kind: Secret`. `gitleaks` runs in pre-commit and CI.
- **Verify, then claim.** A step is done when its command has been run and its output shown; a decision record (`docs/decisions/`) exists for every Claude Code component.
- **Ports** are picked with `scripts/ports.sh`, never hardcoded.
- **Ask before** anything that needs `sudo`, creates a GitHub resource, or pushes to `origin`.
