#!/usr/bin/env bash
# Render dex/dev-config.yaml.tmpl with the project's ports. Spec: 002-flagpole-web (research F5).
# Dex reads a static file and cannot expand environment variables itself, so changing FLAGPOLE_WEB_PORT
# would otherwise break sign-in inside Dex with a redirect-URI mismatch and no message in the app.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && set -a && source "$ROOT/.env" && set +a
export FLAGPOLE_WEB_PORT="${FLAGPOLE_WEB_PORT:-18010}"
export FLAGPOLE_DEX_PORT="${FLAGPOLE_DEX_PORT:-18030}"
rendered="$ROOT/dex/.dev-config.yaml"
previous=""
[[ -f "$rendered" ]] && previous="$(cat "$rendered")"
# shellcheck disable=SC2016  # the single quotes are envsubst's variable whitelist, not an expansion
envsubst '${FLAGPOLE_WEB_PORT} ${FLAGPOLE_DEX_PORT}' \
  < "$ROOT/dex/dev-config.yaml.tmpl" > "$rendered"

# Dex reads its config once at startup and compose sees no change when only the mounted file's
# contents differ, so a running container would keep serving the previous ports.
if [[ "$previous" != "$(cat "$rendered")" ]] &&
   [[ -n "$(docker compose -f "$ROOT/docker-compose.dev.yaml" ps -q dex 2>/dev/null)" ]]; then
  docker compose -f "$ROOT/docker-compose.dev.yaml" restart dex >/dev/null
  echo "dex config changed: container restarted"
fi
echo "dex config rendered for web :$FLAGPOLE_WEB_PORT, dex :$FLAGPOLE_DEX_PORT"
