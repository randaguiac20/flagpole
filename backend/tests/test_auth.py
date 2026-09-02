"""FR-011, FR-012 — authentication and the single role check. Spec: 001-flagpole-api."""

from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tests.conftest import create_flag

UNAUTH = {"detail": "missing or invalid token"}


async def test_missing_and_malformed(client):
    assert (await client.get("/flags")).status_code == 401
    r = await client.get("/flags", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401 and r.json() == UNAUTH
    r = await client.get("/flags", headers={"Authorization": "Basic abc"})
    assert r.status_code == 401


async def test_wrong_issuer_audience_expired(client, make_token):
    for tok in (
        make_token(issuer="https://evil.local"),
        make_token(audience="other-app"),
        make_token(exp_delta=-10),
    ):
        r = await client.get("/flags", headers={"Authorization": f"Bearer {tok}"})
        assert r.status_code == 401 and r.json() == UNAUTH


async def test_other_key_rejected(client, make_token):
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048).private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    tok = make_token(key=other)
    r = await client.get("/flags", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401


async def test_groups_decide_role(client, make_token):
    op = {"Authorization": f"Bearer {make_token(sub='x', groups=('operators',))}"}
    assert (await create_flag(client, op, "by_operator")).status_code == 201
    viewer = {"Authorization": f"Bearer {make_token(sub='y', groups=('team-a',))}"}
    assert (await create_flag(client, viewer, "by_viewer")).status_code == 403
    no_groups = {"Authorization": f"Bearer {make_token(sub='z')}"}
    assert (await create_flag(client, no_groups, "by_nobody")).status_code == 403
    assert (await client.get("/flags", headers=no_groups)).status_code == 200


async def test_identity_falls_back_to_sub(client, make_token):
    op = {"Authorization": f"Bearer {make_token(sub='sub-only', groups=('operators',))}"}
    await create_flag(client, op, "flag_f")
    items = (await client.get("/audit", headers=op)).json()["items"]
    assert items[0]["who"] == "sub-only"


def test_no_validation_bypass_in_source():
    src = "".join(p.read_text() for p in (Path(__file__).parents[1] / "app").rglob("*.py"))
    for forbidden in ("AUTH_DISABLED", 'verify_signature": False', "auth_disabled"):
        assert forbidden not in src
    assert src.count("HTTP_403_FORBIDDEN") == 1  # FR-012: exactly one role check
