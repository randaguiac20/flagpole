---
paths:
  - "backend/**/*.py"
  - "consumer/**/*.py"
  - "mcp/**/*.py"
---

# Python services (flagpole-api, flagpole-consumer, flagpole-mcp)

Loaded only when a Python file in one of these trees is read. Conventions that are true for all three services:

- Python 3.12, managed with `uv`. Run everything through `uv run` inside the service directory; never `pip install`.
- Every module docstring names the spec it implements, e.g. `"""Flag evaluation. Spec: 001-flagpole-api FR-004."""`.
- FastAPI: request/response bodies are Pydantic models in `schemas.py`; no raw dicts across the API boundary.
- Authorization is one dependency (`require_role("operator")`). Never re-check roles inline in a route.
- Errors: raise `HTTPException` with a stable `detail` string that tests assert on. No bare `except:`.
- Logging: `logging.getLogger(__name__)`, never `print`. No secrets, tokens, or `Authorization` headers in logs.
- Evaluation is deterministic: `sha256(f"{flag_key}:{user_id}")` bucketed to 0–99. Never use `random` in evaluation code.
- Tests: `pytest` + `httpx.AsyncClient`, SQLite in a temp file, no network. A test file mirrors the module it tests (`test_flags.py` ↔ `flags.py`).
- Format/lint: `ruff format` + `ruff check --fix` (the PostToolUse hook formats on every edit; CI rejects unformatted code).
- Migrations: schema changes go through Alembic; never edit `Base.metadata.create_all` into production paths.
