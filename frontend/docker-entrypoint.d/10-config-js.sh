#!/bin/sh
# Writes /config.js from the environment, before nginx starts. Spec: 005-platform-delivery FR-011.
#
# The image ships a development copy of this file; here it is replaced with this deployment's values.
# It exists because import.meta.env is inlined at build time (gotcha #12): a build-time value would
# mean one image per environment, and the whole point of the overlay is that there is one image.
set -eu

# Written under /tmp, which is writable even with a read-only root filesystem. nginx serves it from
# here by alias; see nginx.conf.
mkdir -p /tmp/flagpole
target=/tmp/flagpole/config.js
issuer="${FLAGPOLE_OIDC_ISSUER:?FLAGPOLE_OIDC_ISSUER must be set}"
client="${FLAGPOLE_OIDC_CLIENT_ID:-flagpole-web}"

cat > "$target" <<JS
// Written at container start from the environment. Do not edit: rewritten on every start.
window.__FLAGPOLE_CONFIG__ = {
  oidcIssuer: "$issuer",
  oidcClientId: "$client",
};
JS

echo "config.js: issuer=$issuer client=$client"
