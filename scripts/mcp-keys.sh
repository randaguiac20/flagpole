#!/usr/bin/env bash
# Generates the flagpole-mcp service key pair for local development.
# Spec 004-flagpole-mcp, research D2: its own pair, not the consumer's, so revoking the assistant's
# access does not stop the consumer serving pages. Idempotent, so scripts/dev.sh can call it every time.
set -euo pipefail

keys_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/mcp/flagpole-mcp/.keys"
private="$keys_dir/service.key"
public="$keys_dir/service.pub"

mkdir -p "$keys_dir"
if [[ -s "$private" && -s "$public" ]]; then
  echo "mcp keys: already present in $keys_dir"
  exit 0
fi

openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$private" 2>/dev/null
openssl rsa -in "$private" -pubout -out "$public" 2>/dev/null
chmod 600 "$private"
chmod 644 "$public"
echo "mcp keys: generated $private and $public"
