"""contracts/openapi.yaml ↔ app.openapi(). Spec: 001-flagpole-api (plan §contracts)."""

from pathlib import Path

import yaml

CONTRACT = Path(__file__).resolve().parents[2] / "specs/001-flagpole-api/contracts/openapi.yaml"
METHODS = {"get", "post", "put", "delete", "patch"}


def _ops(paths: dict) -> set[tuple[str, str, str]]:
    out = set()
    for path, item in paths.items():
        if path == "/metrics":  # excluded from the generated schema on purpose
            continue
        for method, op in item.items():
            if method in METHODS:
                for code in op.get("responses", {}):
                    if str(code) != "422":  # FastAPI adds 422 by default; we map it to 400
                        out.add((path, method, str(code)))
    return out


def test_generated_schema_matches_contract(app):
    contract = _ops(yaml.safe_load(CONTRACT.read_text())["paths"])
    generated = _ops(app.openapi()["paths"])
    assert contract - generated == set(), f"in contract, not in app: {contract - generated}"
    assert generated - contract == set(), f"in app, not in contract: {generated - contract}"
