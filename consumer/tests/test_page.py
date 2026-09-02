"""The page. Spec: 003-flagpole-consumer FR-001..FR-006, FR-014 (US1, US3)."""

import httpx
import pytest
from fastapi import FastAPI

from app import client as client_module
from tests.conftest import RecordingFlagService, evaluates_to


async def test_banner_is_shown_when_the_service_says_enabled(
    page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    """FR-004 (US1-1)."""
    response = await page.get("/")
    assert response.status_code == 200
    assert 'data-testid="banner"' in response.text


async def test_banner_is_absent_when_the_service_says_disabled(
    app: FastAPI, page: httpx.AsyncClient
) -> None:
    """FR-004 (US1-2, US1-3)."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        evaluates_to(False, "env_disabled")
    )
    response = await page.get("/")
    assert response.status_code == 200
    assert 'data-testid="banner"' not in response.text


async def test_the_service_is_asked_the_documented_question(
    page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    """FR-002: the flag key, the consumer's environment, and the user."""
    await page.get("/?user=alice@flagpole.local")
    assert flag_service.last_body == {
        "flag_key": "new_banner",
        "env": "dev",
        "user_id": "alice@flagpole.local",
    }
    assert str(flag_service.requests[-1].url).endswith("/evaluate")


async def test_the_request_carries_a_bearer_token(
    page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    """FR-010: the consumer authenticates as itself."""
    await page.get("/")
    authorization = flag_service.last_authorization
    assert authorization is not None
    assert authorization.startswith("Bearer ey")


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("", "demo@flagpole.local"),
        ("?user=", "demo@flagpole.local"),
        ("?user=%20%20", "demo@flagpole.local"),
    ],
)
async def test_the_default_user_is_used_when_none_is_given(
    page: httpx.AsyncClient, flag_service: RecordingFlagService, query: str, expected: str
) -> None:
    """FR-001 and the blank-user edge case."""
    await page.get(f"/{query}")
    assert flag_service.last_body["user_id"] == expected


async def test_every_load_asks_the_service_again(
    app: FastAPI, page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    """FR-003, SC-001: nothing is cached, so an operator's change shows on the very next load."""
    first = await page.get("/")
    assert 'data-testid="banner"' in first.text
    assert len(flag_service.requests) == 1

    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        evaluates_to(False, "env_disabled")
    )
    second = await page.get("/")
    assert 'data-testid="banner"' not in second.text


async def test_the_decision_panel_states_what_was_applied(
    page: httpx.AsyncClient,
) -> None:
    """FR-005 (US3-1), every anchor in contracts/page-contract.md."""
    response = await page.get("/?user=alice@flagpole.local")
    text = response.text
    for testid, value in (
        ("decision-flag", "new_banner"),
        ("decision-env", "dev"),
        ("decision-user", "alice@flagpole.local"),
        ("decision-enabled", "true"),
        ("decision-reason", "rollout_hit"),
    ):
        assert f'data-testid="{testid}"' in text
        assert value in text


@pytest.mark.parametrize("reason", ["env_disabled", "rollout_hit", "rollout_miss", "unknown_flag"])
async def test_every_reason_reaches_the_page_unchanged(
    app: FastAPI, page: httpx.AsyncClient, reason: str
) -> None:
    """FR-006: the consumer passes the service's reason through and invents nothing."""
    app.dependency_overrides[client_module.get_transport] = lambda: httpx.MockTransport(
        evaluates_to(reason == "rollout_hit", reason)
    )
    response = await page.get("/")
    assert reason in response.text


async def test_a_user_containing_markup_is_escaped(
    page: httpx.AsyncClient,
) -> None:
    """FR-014: request data renders as text and cannot change the page structure."""
    response = await page.get("/?user=<script>alert(1)</script>")
    assert "<script>alert(1)</script>" not in response.text
    assert "&lt;script&gt;" in response.text


async def test_the_page_never_leaks_the_credential(
    page: httpx.AsyncClient, flag_service: RecordingFlagService
) -> None:
    """SC-006, FR-008."""
    response = await page.get("/")
    token = (flag_service.last_authorization or "").removeprefix("Bearer ")
    assert token
    assert token not in response.text
    for secret in ("BEGIN PRIVATE KEY", "Authorization", "service.key"):
        assert secret not in response.text
