"""Signs the short-lived service token. Spec: 004-flagpole-mcp FR-011; research D2.

The claim set is the one feature 003 defined and both suites assert against
specs/003-flagpole-consumer/contracts/service-token.json. This server signs with its own key pair
and its own issuer name, so revoking it does not touch the consumer and the audit trail can tell
the two apart.
"""

import time

import jwt

LIFETIME_SECONDS = 300


class ServiceTokenSigner:
    def __init__(self, private_key_pem: str, issuer: str, audience: str, env: str) -> None:
        self._key = private_key_pem
        self._issuer = issuer
        self._audience = audience
        self._env = env

    def mint(self) -> str:
        """A fresh token per outbound call. No cache, so no expiry race and no invalidation."""
        now = int(time.time())
        return jwt.encode(
            {
                "iss": self._issuer,
                "sub": self._issuer,
                "aud": self._audience,
                "env": self._env,
                "iat": now,
                "exp": now + LIFETIME_SECONDS,
            },
            self._key,
            algorithm="RS256",
        )
