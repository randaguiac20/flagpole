#!/usr/bin/env bash
# ports.sh — the only way this repo picks or checks a TCP port (PROMPT.md §5.6: "never hardcode a port unchecked").
#
#   scripts/ports.sh check <port>        exit 0 if free, 1 if in use (prints the listener)
#   scripts/ports.sh pick [range]        print the first free port in FLAGPOLE_PORT_RANGE (default 18000-18099)
#   scripts/ports.sh table               print the project port table from .env.example with live status
set -euo pipefail

RANGE_DEFAULT="18000-18099"
ENV_FILE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/.env.example"

listener() { ss -ltnH 2>/dev/null | awk -v p=":$1" '$4 ~ p"$" {print $4; exit}'; }

check() {
  local port="$1"
  if [[ -n "$(listener "$port")" ]]; then
    echo "port $port is IN USE ($(listener "$port"))" >&2
    return 1
  fi
  echo "port $port is free"
}

pick() {
  local range="${1:-${FLAGPOLE_PORT_RANGE:-$RANGE_DEFAULT}}"
  local lo="${range%-*}" hi="${range#*-}"
  for ((p = lo; p <= hi; p++)); do
    if [[ -z "$(listener "$p")" ]]; then echo "$p"; return 0; fi
  done
  echo "no free port in $range" >&2
  return 1
}

table() {
  printf "%-28s %-6s %s\n" "VARIABLE" "PORT" "STATUS"
  grep -E '^FLAGPOLE_[A-Z_]+_PORT=' "$ENV_FILE" | while IFS='=' read -r k v; do
    if [[ -n "$(listener "$v")" ]]; then s="in use"; else s="free"; fi
    printf "%-28s %-6s %s\n" "$k" "$v" "$s"
  done
}

case "${1:-}" in
  check) check "${2:?port required}" ;;
  pick) pick "${2:-}" ;;
  table) table ;;
  *) sed -n '2,7p' "$0"; exit 2 ;;
esac
