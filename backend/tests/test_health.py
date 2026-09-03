"""US4 — liveness, readiness, metrics. Spec: 001-flagpole-api FR-013."""

from app.db import get_session, make_engine, make_sessionmaker
from tests.conftest import create_flag, set_env


async def test_us4_1_healthz_without_token(client):
    r = await client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_us4_2_readyz_reflects_database(app, client):
    assert (await client.get("/readyz")).status_code == 200
    broken = make_sessionmaker(make_engine("sqlite:////nonexistent-dir/x/y/z.db"))

    def broken_session():
        s = broken()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_session] = broken_session
    try:
        r = await client.get("/readyz")
    finally:
        del app.dependency_overrides[get_session]
    assert r.status_code == 503 and r.json() == {"detail": "database unreachable"}


async def test_us4_3_metrics_exposed(client, operator_headers, viewer_headers):
    await create_flag(client, operator_headers, "flag_m")
    await set_env(client, operator_headers, "flag_m", "dev", True, 100)
    await client.post(
        "/evaluate",
        json={"flag_key": "flag_m", "env": "dev", "user_id": "u"},
        headers=viewer_headers,
    )
    text = (await client.get("/metrics")).text
    assert "http_request_duration_seconds" in text
    assert 'flagpole_evaluations_total{env="dev",reason="rollout_hit"}' in text
