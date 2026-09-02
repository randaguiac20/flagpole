"""US2 — deterministic evaluation. Spec: 001-flagpole-api FR-008..010, SC-002, SC-005."""

import hashlib

import pytest

from app.evaluation import bucket, evaluate
from app.schemas import Reason
from tests.conftest import create_flag, set_env


def test_bucket_matches_documented_rule():
    expected = int.from_bytes(hashlib.sha256(b"new_banner:alice").digest(), "big") % 100
    assert bucket("new_banner", "alice") == expected
    assert 0 <= bucket("x", "y") < 100


def test_evaluate_pure_function():
    assert evaluate(False, 100, "f", "u") == (False, Reason.env_disabled)
    assert evaluate(True, 100, "f", "u") == (True, Reason.rollout_hit)
    assert evaluate(True, 0, "f", "u") == (False, Reason.rollout_miss)
    b = bucket("f", "u")
    assert evaluate(True, b, "f", "u") == (False, Reason.rollout_miss)
    assert evaluate(True, b + 1, "f", "u") == (True, Reason.rollout_hit)


def test_sc002_distribution_at_50_percent():
    hits = sum(1 for i in range(10_000) if evaluate(True, 50, "new_banner", f"u-{i}")[0])
    assert 0.45 <= hits / 10_000 <= 0.55


@pytest.fixture
async def seeded(client, operator_headers):
    await create_flag(client, operator_headers, "new_banner")
    await set_env(client, operator_headers, "new_banner", "dev", True, 50)
    return client


async def ev(client, headers, flag_key="new_banner", env="dev", user_id="alice"):
    return await client.post(
        "/evaluate", json={"flag_key": flag_key, "env": env, "user_id": user_id}, headers=headers
    )


async def test_us2_1_env_disabled(seeded, viewer_headers):
    r = await ev(seeded, viewer_headers, env="prod")
    assert r.status_code == 200 and r.json() == {"enabled": False, "reason": "env_disabled"}


async def test_us2_2_matches_bucket_rule(seeded, viewer_headers):
    r = await ev(seeded, viewer_headers, user_id="alice")
    expected = bucket("new_banner", "alice") < 50
    assert r.json() == {
        "enabled": expected,
        "reason": "rollout_hit" if expected else "rollout_miss",
    }


async def test_us2_3_hundred_identical_answers(seeded, viewer_headers):
    answers = {(await ev(seeded, viewer_headers)).text for _ in range(100)}
    assert len(answers) == 1


async def test_us2_4_full_and_zero_rollout(seeded, operator_headers, viewer_headers):
    await set_env(seeded, operator_headers, "new_banner", "dev", True, 100)
    for u in ("a", "b", "c"):
        assert (await ev(seeded, viewer_headers, user_id=u)).json()["reason"] == "rollout_hit"
    await set_env(seeded, operator_headers, "new_banner", "dev", True, 0)
    for u in ("a", "b", "c"):
        assert (await ev(seeded, viewer_headers, user_id=u)).json()["reason"] == "rollout_miss"


async def test_us2_5_unknown_flag_fails_safe(client, viewer_headers):
    r = await ev(client, viewer_headers, flag_key="does_not_exist")
    assert r.status_code == 200 and r.json() == {"enabled": False, "reason": "unknown_flag"}


async def test_us2_6_unauthenticated(client):
    r = await ev(client, {})
    assert r.status_code == 401 and r.json() == {"detail": "missing or invalid token"}


async def test_unknown_env_is_invalid(seeded, viewer_headers):
    r = await ev(seeded, viewer_headers, env="staging")
    assert r.status_code == 400 and r.json()["detail"].startswith("invalid input")
