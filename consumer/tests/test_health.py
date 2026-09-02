"""Health that does not depend on the flag service. Spec: 003 FR-013 (US2)."""

import httpx
from fastapi import FastAPI

from app import client as client_module
from tests.conftest import RecordingFlagService


async def test_healthz_is_ok(page: httpx.AsyncClient) -> None:
    response = await page.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_readyz_is_ok_while_the_flag_service_is_down(
    app: FastAPI, page: httpx.AsyncClient
) -> None:
    """FR-013: a readiness probe that failed here would remove the consumer from service.

    That is precisely when US2 says it must keep serving, so readiness must not depend on upstream.
    """

    def refuse(request: httpx.Request) -> httpx.Response:  # noqa: ARG001 - always fails
        raise httpx.ConnectError("connection refused")

    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(refuse)
    response = await page.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_makes_no_outbound_call(
    page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    await page.get("/healthz")
    await page.get("/readyz")
    assert flag_service.requests == []
