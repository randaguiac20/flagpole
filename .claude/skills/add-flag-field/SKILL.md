---
name: add-flag-field
description: Checklist for adding a new field to a flag or its per-environment state end to end - spec, model, migration, API schema, MCP tool, UI, tests. Use whenever a change touches the flag data model so nothing is forgotten.
argument-hint: "<field-name> <type> [description]"
---

A flag field crosses every layer of Flagpole. Work through this list in order and tick each item in your reply. Field: `$0`, type: `$1`.

1. **Spec first.** Which spec owns it? Usually `specs/001-flagpole-api/spec.md` (data + API) and `specs/002-flagpole-web/spec.md` (UI). Add or amend the FR and an acceptance scenario. If the change is user-visible and non-trivial, it needs its own `/speckit-specify` run instead of an amendment.
2. **Model**: `backend/app/models.py` — column with a server default so existing rows stay valid.
3. **Migration**: `cd backend && uv run alembic revision --autogenerate -m "add <field>"`; read the generated file; `uv run alembic upgrade head` against a scratch SQLite DB.
4. **Schemas**: `backend/app/schemas.py` request + response models; keep `PUT /flags/{key}/env/{env}` backward compatible (new field optional).
5. **Audit log**: if the field is part of per-environment state, `before`/`after` snapshots in `audit_log` must include it.
6. **Evaluation**: does the field change `/evaluate`? If yes, update the rule in the spec and the deterministic function together, and add a table-driven test.
7. **MCP**: `mcp/flagpole-mcp` — `list_flags` output and `toggle_flag`/`evaluate_flag` arguments; update the `flags://{env}` resource and the tool tests.
8. **UI**: `frontend/src` — table column and the editor control (disabled for viewers), with a `data-testid`; unit test for the control.
9. **Seed data**: `deploy/overlays/*/seed-job` and `backend/app/seed.py` (the `new_banner` flag) if the field needs a value.
10. **Tests & docs**: pytest, Vitest, one Playwright scenario if user-visible; run `/speckit-analyze` if a spec changed; update `docs/walkthrough.md` only if the demo path changed.
