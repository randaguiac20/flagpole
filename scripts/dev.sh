#!/usr/bin/env bash
# make dev — local development stack. Feature 001 starts the API; 002 adds web + Dex (docker compose); 003 the consumer.
# Every port is checked with scripts/ports.sh before anything binds it.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a
API_PORT="${FLAGPOLE_API_PORT:-18000}"

scripts/ports.sh check "$API_PORT"
echo "== flagpole-api on :$API_PORT (FLAGPOLE_DATABASE_URL=${FLAGPOLE_DATABASE_URL:-sqlite:///./flagpole.db})"
(
  cd backend
  uv run alembic upgrade head
  uv run python -m app.seed
  exec uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port "$API_PORT" --reload
)
