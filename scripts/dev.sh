#!/usr/bin/env bash
# make dev — the local stack for specs 001-flagpole-api and 002-flagpole-web.
#   Dex (docker compose)   :18030   identity provider, two static demo users
#   flagpole-api (uvicorn) :18000   migrated and seeded on start
#   flagpole-web (Vite)    :18010   proxies /api -> the API
# Every port is checked with scripts/ports.sh before anything binds it. Ctrl-C stops everything.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
[[ -f .env ]] && set -a && source .env && set +a
API_PORT="${FLAGPOLE_API_PORT:-18000}"
WEB_PORT="${FLAGPOLE_WEB_PORT:-18010}"
CONSUMER_PORT="${FLAGPOLE_CONSUMER_PORT:-18020}"
DEX_PORT="${FLAGPOLE_DEX_PORT:-18030}"

pids=()
cleanup() {
  for pid in "${pids[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  echo "== stopped (Dex is still running: docker compose -f docker-compose.dev.yaml down)"
}
# EXIT alone: INT and TERM both end in EXIT, and trapping all three ran cleanup twice.
trap cleanup EXIT

scripts/dex-config.sh
scripts/consumer-keys.sh

echo "== identity provider on :$DEX_PORT"
if ! curl -sf "http://localhost:$DEX_PORT/dex/.well-known/openid-configuration" >/dev/null 2>&1; then
  scripts/ports.sh check "$DEX_PORT"
  docker compose -f docker-compose.dev.yaml up -d dex
  for _ in $(seq 1 30); do
    curl -sf "http://localhost:$DEX_PORT/dex/.well-known/openid-configuration" >/dev/null 2>&1 && break
    sleep 1
  done
fi

echo "== flagpole-api on :$API_PORT"
scripts/ports.sh check "$API_PORT"
(
  cd backend
  # Trust the consumer's key as a second issuer for services (001 FR-019).
  export FLAGPOLE_SERVICE_ISSUER="${FLAGPOLE_SERVICE_ISSUER:-flagpole-consumer}"
  export FLAGPOLE_SERVICE_AUDIENCE="${FLAGPOLE_SERVICE_AUDIENCE:-flagpole-api}"
  export FLAGPOLE_SERVICE_PUBLIC_KEY_PATH="${FLAGPOLE_SERVICE_PUBLIC_KEY_PATH:-../consumer/.keys/service.pub}"
  export FLAGPOLE_SERVICE_ENV="${FLAGPOLE_CONSUMER_ENV:-dev}"  # a token for the other env is refused
  uv run alembic upgrade head
  uv run python -m app.seed
  exec uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port "$API_PORT" --reload
) &
pids+=($!)

echo "== flagpole-consumer on :$CONSUMER_PORT"
scripts/ports.sh check "$CONSUMER_PORT"
(
  cd consumer
  export FLAGPOLE_API_URL="${FLAGPOLE_API_URL:-http://127.0.0.1:$API_PORT}"
  exec uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port "$CONSUMER_PORT" --reload
) &
pids+=($!)

echo "== flagpole-web on :$WEB_PORT"
scripts/ports.sh check "$WEB_PORT"
(cd frontend && exec npm run dev) &
pids+=($!)

cat <<MSG

  Web       http://localhost:$WEB_PORT
  Consumer  http://localhost:$CONSUMER_PORT
  API       http://localhost:$API_PORT/openapi.json
  Dex       http://localhost:$DEX_PORT/dex/.well-known/openid-configuration

  Demo users (local only): alice@flagpole.local / flagpole  (operators)
                           bob@flagpole.local   / flagpole  (viewers)
MSG
wait
