"""US1 — operator manages a flag's rollout. Spec: 001-flagpole-api FR-001..005, FR-014, FR-018."""

from tests.conftest import create_flag, set_env


async def test_us1_1_create_flag_starts_disabled(client, operator_headers):
    r = await create_flag(client, operator_headers, "new_banner", "Demo banner")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["key"] == "new_banner"
    assert body["description"] == "Demo banner"
    assert body["created_at"].endswith("Z")
    assert body["environments"] == {
        "dev": {"enabled": False, "rollout_percent": 0},
        "prod": {"enabled": False, "rollout_percent": 0},
    }


async def test_us1_2_duplicate_is_conflict(client, operator_headers):
    assert (await create_flag(client, operator_headers, "dup")).status_code == 201
    r = await create_flag(client, operator_headers, "dup", "again")
    assert r.status_code == 409
    assert r.json() == {"detail": "flag already exists"}
    flags = (await client.get("/flags", headers=operator_headers)).json()
    assert [f["description"] for f in flags if f["key"] == "dup"] == ["d"]


async def test_us1_3_set_dev_state_and_audit(client, operator_headers):
    await create_flag(client, operator_headers, "new_banner")
    r = await set_env(client, operator_headers, "new_banner", "dev", True, 25)
    assert r.status_code == 200, r.text
    assert r.json()["environments"]["dev"] == {"enabled": True, "rollout_percent": 25}
    assert r.json()["environments"]["prod"] == {"enabled": False, "rollout_percent": 0}
    audit = (await client.get("/audit", headers=operator_headers)).json()["items"]
    assert audit[0]["who"] == "alice@flagpole.local"
    assert audit[0]["flag_key"] == "new_banner"
    assert audit[0]["env"] == "dev"
    assert audit[0]["before"] == {"enabled": False, "rollout_percent": 0}
    assert audit[0]["after"] == {"enabled": True, "rollout_percent": 25}
    assert audit[0]["at"].endswith("Z")
    # creation entry (FR-005): env null, before null
    assert audit[1]["env"] is None and audit[1]["before"] is None
    assert audit[1]["after"] == {"description": "d"}


async def test_us1_4_invalid_values_rejected_without_audit(client, operator_headers):
    await create_flag(client, operator_headers, "flag_f")
    before = len((await client.get("/audit", headers=operator_headers)).json()["items"])
    for env, rollout in (("dev", 101), ("dev", -1), ("staging", 10)):
        r = await set_env(client, operator_headers, "flag_f", env, True, rollout)
        assert r.status_code == 400, (env, rollout, r.text)
        assert r.json()["detail"].startswith("invalid input")
    after = len((await client.get("/audit", headers=operator_headers)).json()["items"])
    assert after == before


async def test_us1_5_viewer_cannot_write(client, operator_headers, viewer_headers):
    await create_flag(client, operator_headers, "flag_f")
    r = await create_flag(client, viewer_headers, "flag_g")
    assert r.status_code == 403 and r.json() == {"detail": "operator role required"}
    r = await set_env(client, viewer_headers, "flag_f", "dev", True, 10)
    assert r.status_code == 403
    items = (await client.get("/audit", headers=viewer_headers)).json()["items"]
    assert len(items) == 1  # only the creation by the operator


async def test_us1_6_identical_put_twice_audits_twice(client, operator_headers):
    await create_flag(client, operator_headers, "flag_f")
    for _ in range(2):
        assert (
            await set_env(client, operator_headers, "flag_f", "dev", True, 25)
        ).status_code == 200
    items = (await client.get("/audit", headers=operator_headers)).json()["items"]
    assert len(items) == 3
    assert items[0]["before"] == items[0]["after"] == {"enabled": True, "rollout_percent": 25}


async def test_unknown_flag_put_is_404(client, operator_headers):
    r = await set_env(client, operator_headers, "nope", "dev", True, 1)
    assert r.status_code == 404 and r.json() == {"detail": "unknown flag"}


async def test_fr014_key_and_description_validation(client, operator_headers):
    for bad in ("Bad", "1abc", "a", "x" * 64, "with-dash"):
        r = await create_flag(client, operator_headers, bad)
        assert r.status_code == 400, bad
    r = await create_flag(client, operator_headers, "ok_key", "x" * 201)
    assert r.status_code == 400
    r = await create_flag(client, operator_headers, "ok_key", "")
    assert r.status_code == 201


async def test_fr006_list_ordered_by_key(client, operator_headers, viewer_headers):
    for k in ("zeta", "alpha", "mid"):
        await create_flag(client, operator_headers, k)
    keys = [f["key"] for f in (await client.get("/flags", headers=viewer_headers)).json()]
    assert keys == ["alpha", "mid", "zeta"]
