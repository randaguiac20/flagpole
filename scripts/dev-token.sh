#!/usr/bin/env bash
# Mints a real token for a demo user against the LOCAL Dex, so the curl scenarios in
# specs/001-flagpole-api/quickstart.md can actually be run by a human.
#
# specs/001-flagpole-api/quickstart.md has named this script since feature 001, as arriving "in
# feature 002/003". Both shipped; this did not. Five of that page's seven scenarios need a bearer
# token, and the only other token source in the repository is a pytest fixture, which is not
# something you can call from a shell. So the page's own instructions could not be followed.
#
# It is the same authorization-code + PKCE exchange the browser performs — no password grant, no
# client secret, nothing the real client does not do. Local development only: it talks to
# http://localhost, and the credentials it uses are printed in the walkthrough.
#
#   scripts/dev-token.sh                 # alice (operator), access token
#   scripts/dev-token.sh bob             # bob (viewer)
#   scripts/dev-token.sh alice --id      # the id_token instead
#   scripts/dev-token.sh alice --claims  # decode and show, mint nothing usable
#
#   OP=$(scripts/dev-token.sh alice) && curl -s localhost:18000/flags -H "Authorization: Bearer $OP"
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1
# shellcheck disable=SC1091
[[ -f .env ]] && source .env

DEX_PORT="${FLAGPOLE_DEX_PORT:-18030}"
WEB_PORT="${FLAGPOLE_WEB_PORT:-18010}"
ISSUER="http://localhost:${DEX_PORT}/dex"
REDIRECT="http://localhost:${WEB_PORT}/callback"   # must be one Dex lists, or it refuses the code
CLIENT="flagpole-web"

user="${1:-alice}"; [[ "$user" == -* ]] && user="alice"
want="access"
for arg in "$@"; do
  case "$arg" in
    --id)     want="id" ;;
    --claims) want="claims" ;;
  esac
done
case "$user" in
  alice|alice@flagpole.local) login="alice@flagpole.local" ;;
  bob|bob@flagpole.local)     login="bob@flagpole.local" ;;
  *) echo "unknown user '$user' — the static users are alice (operator) and bob (viewer)" >&2; exit 1 ;;
esac

die() { printf '%s\n' "$1" >&2; exit 1; }
command -v jq >/dev/null || die "jq is required"
curl -sf "$ISSUER/.well-known/openid-configuration" >/dev/null 2>&1 \
  || die "Dex is not answering on $ISSUER — start it with: make dev"

# PKCE: a fresh verifier per run, and its S256 challenge. The public client has no secret, so this
# is the only thing binding the code to whoever asked for it.
pkce="$(python3 - <<'PY'
import base64, hashlib, secrets
v = base64.urlsafe_b64encode(secrets.token_bytes(48)).rstrip(b'=').decode()
print(v)
print(base64.urlsafe_b64encode(hashlib.sha256(v.encode()).digest()).rstrip(b'=').decode())
PY
)" || die "could not generate a PKCE pair (python3 required)"
verifier="$(sed -n 1p <<<"$pkce")"; challenge="$(sed -n 2p <<<"$pkce")"

jar="$(mktemp)"; trap 'rm -f "$jar"' EXIT

# 1. /auth, following redirects to Dex's login form. The password connector puts the form at a URL
#    carrying the request state, so the form's own URL is what the credentials are posted back to.
form="$(curl -sS -c "$jar" -b "$jar" -o /dev/null -w '%{url_effective}' -L -G "$ISSUER/auth" \
  --data-urlencode "client_id=$CLIENT" \
  --data-urlencode "redirect_uri=$REDIRECT" \
  --data-urlencode "response_type=code" \
  --data-urlencode "scope=openid profile email groups" \
  --data-urlencode "state=dev-token" \
  --data-urlencode "code_challenge=$challenge" \
  --data-urlencode "code_challenge_method=S256")" || die "the authorize request failed"
[[ "$form" == *"/auth/local"* ]] || die "Dex did not present the local login form (got: $form)"

# 2. Post the credentials, then walk the redirect chain BY HAND. `curl -L` cannot be used here:
#    the last hop points at the web app on :18010, which is not running when someone is following
#    the API's quickstart, and curl would fail trying to fetch it. The code is in the Location
#    header — reading it is the point, following it is not.
hop() { # hop <url> [post-args...] -> prints the Location header, absolutised
  local url="$1"; shift
  local loc
  loc="$(curl -sS -c "$jar" -b "$jar" -o /dev/null -D - "$@" "$url" \
        | awk 'tolower($1) == "location:" { print $2 }' | tr -d '\r' | tail -1)"
  case "$loc" in
    /*) printf 'http://localhost:%s%s\n' "$DEX_PORT" "$loc" ;;
    *)  printf '%s\n' "$loc" ;;
  esac
}

next="$(hop "$form" --data-urlencode "login=$login" --data-urlencode "password=flagpole")"
[[ -n "$next" ]] || die "the login post returned no redirect — wrong password, or Dex changed its form"

# Dex sends login -> /approval -> redirect_uri. skipApprovalScreen means /approval does not stop,
# but it is still a hop. A handful of iterations is plenty; looping forever on a redirect loop is not.
for _ in 1 2 3 4 5; do
  case "$next" in
    "$REDIRECT"*) break ;;
    "") die "the redirect chain ended without reaching $REDIRECT" ;;
  esac
  next="$(hop "$next")"
done
case "$next" in
  *"code="*) ;;
  *) die "no authorization code came back — check the demo password, or Dex's redirectURIs (wanted $REDIRECT)" ;;
esac
code="$(sed -E 's/.*[?&]code=([^&]*).*/\1/' <<<"$next")"

# 3. Exchange. Public client: the verifier stands in for a secret.
tokens="$(curl -sS -X POST "$ISSUER/token" \
  -d grant_type=authorization_code -d "client_id=$CLIENT" \
  --data-urlencode "code=$code" \
  --data-urlencode "redirect_uri=$REDIRECT" \
  --data-urlencode "code_verifier=$verifier")" || die "the token exchange failed"
jq -e '.access_token' >/dev/null 2>&1 <<<"$tokens" \
  || die "Dex returned no token: $(head -c 300 <<<"$tokens")"

show() { # decode a JWT payload without verifying it — this is for reading, never for trusting
  python3 -c '
import base64,json,sys
p=sys.argv[1].split(".")[1]; p+="="*(-len(p)%4)
print(json.dumps(json.loads(base64.urlsafe_b64decode(p)), indent=2))' "$1"
}

case "$want" in
  access) jq -r '.access_token' <<<"$tokens" ;;
  id)     jq -r '.id_token'     <<<"$tokens" ;;
  claims)
    echo "=== id_token ===";     show "$(jq -r '.id_token' <<<"$tokens")"
    echo "=== access_token ==="; show "$(jq -r '.access_token' <<<"$tokens")"
    ;;
esac
