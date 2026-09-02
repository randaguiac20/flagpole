"""The one call to the flag service. Spec: 003-flagpole-consumer FR-002, FR-007, FR-008, FR-009.

Everything that can go wrong upstream leaves here as the same safe decision. Nothing raises into the
request path: a broken flag service must never take the product down (US2).
"""

import logging
from dataclasses import dataclass

import httpx
from fastapi import Depends, Request

from app.config import Env, Settings
from app.tokens import ServiceTokenSigner

logger = logging.getLogger(__name__)

SERVICE_UNAVAILABLE = "service_unavailable"
KNOWN_REASONS = frozenset(
    {"env_disabled", "rollout_hit", "rollout_miss", "unknown_flag", SERVICE_UNAVAILABLE}
)


@dataclass(frozen=True)
class Decision:
    """What the consumer acted on for one page load. Never stored (data-model.md)."""

    flag_key: str
    env: Env
    user: str
    enabled: bool
    reason: str
    from_service: bool


def get_transport() -> httpx.BaseTransport | None:
    """The transport for the outbound call; tests replace it with a stub (research C8)."""
    return None


def _unavailable(settings: Settings, user: str, cause: str) -> Decision:
    # The cause goes to the operator, never to the visitor (FR-008).
    logger.warning("flag evaluation failed, falling back to %s: %s", SERVICE_UNAVAILABLE, cause)
    return Decision(
        flag_key=settings.flag_key,
        env=settings.consumer_env,
        user=user,
        enabled=False,
        reason=SERVICE_UNAVAILABLE,
        from_service=False,
    )


class FlagServiceClient:
    def __init__(
        self,
        settings: Settings,
        signer: ServiceTokenSigner,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._signer = signer
        self._transport = transport

    async def evaluate(self, user: str) -> Decision:
        settings = self._settings
        timeout = httpx.Timeout(settings.consumer_timeout_seconds)
        try:
            async with httpx.AsyncClient(
                base_url=settings.api_url, timeout=timeout, transport=self._transport
            ) as client:
                response = await client.post(
                    "/evaluate",
                    json={
                        "flag_key": settings.flag_key,
                        "env": settings.consumer_env,
                        "user_id": user,
                    },
                    headers={"Authorization": f"Bearer {self._signer.mint()}"},
                )
        except httpx.HTTPError as exc:
            return _unavailable(settings, user, f"{type(exc).__name__}: {exc}")

        if response.status_code != 200:
            return _unavailable(settings, user, f"answered {response.status_code}")

        try:
            body = response.json()
            enabled, reason = bool(body["enabled"]), str(body["reason"])
        except (ValueError, KeyError, TypeError) as exc:
            return _unavailable(settings, user, f"unreadable answer: {type(exc).__name__}")

        if reason not in KNOWN_REASONS:
            # An unknown reason means the two services disagree about the contract; fail safe
            # rather than render a decision nobody can explain.
            return _unavailable(settings, user, f"unknown reason {reason!r}")

        return Decision(
            flag_key=settings.flag_key,
            env=settings.consumer_env,
            user=user,
            enabled=enabled,
            reason=reason,
            from_service=True,
        )


def get_client(
    request: Request,
    transport: httpx.BaseTransport | None = Depends(get_transport),
) -> FlagServiceClient:
    return FlagServiceClient(
        settings=request.app.state.settings,
        signer=request.app.state.signer,
        transport=transport,
    )
