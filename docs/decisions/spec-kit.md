# Decision: GitHub Spec Kit v1.0.3 for SDD

- **Problem / trigger**: six user-visible features whose requirements would otherwise live in chat. Spec Kit provides constitution/specify/clarify/plan/tasks/analyze/implement with gates, installed as Claude Code skills.
- **Alternative rejected**: the lightweight `specs/<nnn>/{spec,plan,tasks}.md` fallback with our own `/spec` skill (re-implements what Spec Kit already provides; only if Spec Kit had been rejected).
- **Limits**: pinned `git+https://github.com/github/spec-kit.git@v1.0.3`, `--integration claude --script sh`; we use 8 of the 10 installed skills as gates (`converge` and `taskstoissues` documented, unused); constitution ≠ CLAUDE.md (principles vs operational facts).
- **Not done**: no Spec Kit extensions/presets, no `.specify/extensions.yml` hooks. Signal: a repeated manual step around `/speckit-specify` (e.g. branch creation policy) → a `before_specify` hook.
- **Verification**: `specify version` = 1.0.3; `.claude/skills/speckit-*/SKILL.md` (10) and `.specify/` present; `/speckit-constitution` visible in `/` after restart. Constitution written 2026-09-02.
