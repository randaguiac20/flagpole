"""The calls to flagpole-api. Spec: 004-flagpole-mcp FR-006, FR-009, FR-011a; research D5.

Every failure becomes a named kind with a message an assistant can act on. Nothing is cached: each
call mints a token and asks the flag service (FR-006).
"""

import logging
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import ValidationError

from flagpole_mcp.config import Settings
from flagpole_mcp.schemas import FlagView
from flagpole_mcp.tokens import ServiceTokenSigner

logger = logging.getLogger(__name__)

UNREACHABLE = "unreachable"
UNAUTHORIZED = "unauthorized"
FORBIDDEN = "forbidden"
UNKNOWN_FLAG = "unknown_flag"
INVALID_ARGUMENT = "invalid_argument"
UNEXPECTED_SHAPE = "unexpected_shape"


class FlagServiceError(Exception):
    """A failure with a kind and a message. Carries no token, no key and no traceback (FR-010)."""

    def __init__(self, kind: str, message: str) -> None:
        super().__init__(message)
        self.kind = kind
        self.message = message


@dataclass(frozen=True)
class FlagServiceClient:
    settings: Settings
    signer: ServiceTokenSigner
    transport: httpx.BaseTransport | None = None

    def _request(self, method: str, path: str, json: Any | None = None) -> Any:
        url = self.settings.api_url.rstrip("/")
        try:
            with httpx.Client(
                base_url=url,
                transport=self.transport,
                timeout=self.settings.mcp_timeout_seconds,
            ) as client:
                response = client.request(
                    method,
                    path,
                    json=json,
                    headers={"Authorization": f"Bearer {self.signer.mint()}"},
                )
        except httpx.HTTPError as exc:
            # The exception text can name a host but never a credential; the message says what to
            # do about it, which a stack trace would not.
            logger.warning("flag service at %s could not be reached: %s", url, type(exc).__name__)
            raise FlagServiceError(
                UNREACHABLE, f"The flag service at {url} could not be reached."
            ) from exc
        return self._answer(response, url)

    @staticmethod
    def _answer(response: httpx.Response, url: str) -> Any:
        if response.status_code == 401:
            raise FlagServiceError(
                UNAUTHORIZED,
                f"The flag service at {url} refused this server's credentials. Check that its "
                "issuer and public key are configured there, and that the environments match.",
            )
        if response.status_code == 403:
            raise FlagServiceError(
                FORBIDDEN,
                "This server has not been granted operator rights by the flag service, so it can "
                "read flag state but not change it.",
            )
        if response.status_code == 404:
            raise FlagServiceError(UNKNOWN_FLAG, "The flag service does not have that flag.")
        if response.status_code in (400, 409, 422):
            raise FlagServiceError(
                INVALID_ARGUMENT, f"The flag service refused the request ({response.status_code})."
            )
        if response.status_code >= 400:
            raise FlagServiceError(
                UNREACHABLE,
                f"The flag service at {url} answered {response.status_code}.",
            )
        return response

    @staticmethod
    def _parse_many(response: httpx.Response) -> list[FlagView]:
        try:
            return [FlagView.model_validate(item) for item in response.json()]
        except (ValueError, TypeError, ValidationError) as exc:
            raise FlagServiceError(
                UNEXPECTED_SHAPE,
                "The flag service answered something this server does not recognise. It is "
                "probably a different version than this server expects.",
            ) from exc

    @staticmethod
    def _parse_one(response: httpx.Response) -> FlagView:
        try:
            return FlagView.model_validate(response.json())
        except (ValueError, TypeError, ValidationError) as exc:
            raise FlagServiceError(
                UNEXPECTED_SHAPE,
                "The flag service answered something this server does not recognise. It is "
                "probably a different version than this server expects.",
            ) from exc

    def list_flags(self) -> list[FlagView]:
        return self._parse_many(self._request("GET", "/flags"))

    def get_flag(self, key: str) -> FlagView:
        for flag in self.list_flags():
            if flag.key == key:
                return flag
        raise FlagServiceError(UNKNOWN_FLAG, f"There is no flag called {key!r}.")

    def set_flag_state(self, key: str, env: str, enabled: bool, rollout_percent: int) -> FlagView:
        response = self._request(
            "PUT",
            f"/flags/{key}/env/{env}",
            json={"enabled": enabled, "rollout_percent": rollout_percent},
        )
        return self._parse_one(response)
