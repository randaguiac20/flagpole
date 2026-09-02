"""The service token this consumer signs. Spec: 003-flagpole-consumer FR-010, FR-010b, FR-010c.

The claim set is a contract with the flag service:
specs/003-flagpole-consumer/contracts/service-token.md.
"""

import time

import jwt

from app.config import Settings

# Short enough that a leaked token is nearly worthless (research C2).
TOKEN_LIFETIME_SECONDS = 300


class ServiceTokenSigner:
    """Mints a fresh token per call.

    No cache: it would buy microseconds and cost a clock, an expiry race and an invalidation rule.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        # Read once, so a missing or unreadable key stops startup rather than a page load.
        self._private_key = settings.read_signing_key()

    def mint(self) -> str:
        now = int(time.time())
        # No groups claim, deliberately: it is what makes this token a viewer at the other end
        # (FR-010c). The flag service also ignores groups on service tokens, so this is belt
        # and braces — the ceiling holds even if this line is ever changed.
        return jwt.encode(
            {
                "iss": self._settings.service_issuer,
                "sub": self._settings.service_issuer,
                "aud": self._settings.service_audience,
                "iat": now,
                "exp": now + TOKEN_LIFETIME_SECONDS,
            },
            self._private_key,
            algorithm="RS256",
        )
