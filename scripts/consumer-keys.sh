#!/usr/bin/env bash
# Generate the consumer's service key pair, for feature 003 (FR-010a, research C4).
# Local development only: the cluster gets the same pair as a SOPS-encrypted Secret in feature 005.
# Idempotent, so scripts/dev.sh can call it unconditionally. Prints paths, never key material.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYS="$ROOT/consumer/.keys"
PRIVATE="$KEYS/service.key"
PUBLIC="$KEYS/service.pub"

if [[ -f "$PRIVATE" && -f "$PUBLIC" ]]; then
  echo "consumer keys already present: $PRIVATE"
  exit 0
fi

mkdir -p "$KEYS"
openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 -out "$PRIVATE" 2>/dev/null
openssl rsa -in "$PRIVATE" -pubout -out "$PUBLIC" 2>/dev/null
chmod 700 "$KEYS"
chmod 600 "$PRIVATE"
chmod 644 "$PUBLIC"
echo "consumer keys written: $PRIVATE (private, 0600), $PUBLIC (public)"
