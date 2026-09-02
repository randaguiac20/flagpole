"""Liveness and readiness. Spec: 003-flagpole-consumer FR-013.

Neither calls the flag service. A readiness probe that failed during an upstream outage would remove
this service from the load balancer at exactly the moment US2 says it must keep serving.
"""

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/readyz")
def readyz() -> dict[str, str]:
    return {"status": "ok"}
