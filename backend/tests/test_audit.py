"""US3 — viewer reads flags and the audit trail. Spec: 001-flagpole-api FR-006, FR-007."""

from tests.conftest import create_flag, set_env


async def fill(client, operator_headers):
    await create_flag(client, operator_headers, "flag_a")
    await create_flag(client, operator_headers, "flag_b")
    await set_env(client, operator_headers, "flag_a", "dev", True, 10)
    await set_env(client, operator_headers, "flag_a", "prod", True, 20)
    await set_env(client, operator_headers, "flag_b", "dev", False, 30)


async def test_us3_1_list_as_viewer(client, operator_headers, viewer_headers):
    await fill(client, operator_headers)
    r = await client.get("/flags", headers=viewer_headers)
    assert r.status_code == 200
    assert [f["key"] for f in r.json()] == ["flag_a", "flag_b"]
    assert r.json()[0]["environments"]["prod"] == {"enabled": True, "rollout_percent": 20}


async def test_us3_2_newest_first_with_all_fields(client, operator_headers, viewer_headers):
    await fill(client, operator_headers)
    items = (await client.get("/audit", headers=viewer_headers)).json()["items"]
    assert len(items) == 5
    ids = [i["id"] for i in items]
    assert ids == sorted(ids, reverse=True)
    assert set(items[0]) == {"id", "who", "at", "flag_key", "env", "before", "after"}
    assert items[0]["flag_key"] == "flag_b" and items[0]["env"] == "dev"


async def test_us3_3_cursor_pages_without_gaps(client, operator_headers, viewer_headers):
    await fill(client, operator_headers)
    seen: list[int] = []
    before = None
    for _ in range(10):
        params = {"limit": 2, **({"before": before} if before else {})}
        page = (await client.get("/audit", params=params, headers=viewer_headers)).json()
        seen += [i["id"] for i in page["items"]]
        before = page["next_before"]
        if before is None:
            break
    assert len(seen) == 5 and len(set(seen)) == 5 and seen == sorted(seen, reverse=True)


async def test_us3_4_filter_by_flag_key(client, operator_headers, viewer_headers):
    await fill(client, operator_headers)
    items = (
        await client.get("/audit", params={"flag_key": "flag_a"}, headers=viewer_headers)
    ).json()["items"]
    assert {i["flag_key"] for i in items} == {"flag_a"} and len(items) == 3


async def test_limit_bounds(client, viewer_headers):
    for limit in (0, 201):
        r = await client.get("/audit", params={"limit": limit}, headers=viewer_headers)
        assert r.status_code == 400
    r = await client.get("/audit", headers=viewer_headers)
    assert r.json() == {"items": [], "next_before": None}
