"""The whole surface. Spec: 003-flagpole-consumer FR-015."""

from typing import Any

from fastapi import FastAPI

WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _walk(routes: Any) -> list[Any]:
    """Every route, including those inside included routers.

    This version of FastAPI keeps an included router nested in `app.routes` rather than flattening
    its routes into it, so a shallow pass would miss the pages entirely — and would have reported a
    read-only surface no matter what the routers contained.
    """
    found: list[Any] = []
    for route in routes:
        found.append(route)
        found.extend(_walk(getattr(route, "routes", []) or []))
    return found


def test_the_consumer_exposes_no_write_path(app: FastAPI) -> None:
    """FR-015: read-only by construction, not by convention.

    A consumer that could write would be a second, unaudited way to change a flag. Checking every
    route means a future handler cannot quietly add one.
    """
    offenders = [
        (route.path, sorted(set(route.methods) & WRITE_METHODS))
        for route in _walk(app.routes)
        if getattr(route, "methods", None) and set(route.methods) & WRITE_METHODS
    ]
    assert offenders == []


def test_the_pages_are_exactly_the_documented_ones(app: FastAPI) -> None:
    """contracts/page-contract.md: one page and two health endpoints, nothing else."""
    assert set(app.openapi()["paths"]) == {"/", "/healthz", "/readyz"}


def test_metrics_are_exposed(app: FastAPI) -> None:
    """Excluded from the schema, as in 001, but it must exist."""
    paths = {getattr(route, "path", None) for route in _walk(app.routes)}
    assert "/metrics" in paths
